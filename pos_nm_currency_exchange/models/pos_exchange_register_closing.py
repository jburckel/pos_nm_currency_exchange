# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PosNmExchangeRegisterClosing(models.Model):
    """Closing of the exchange register of a period, for a company or one
    of its exchange offices: the figures of the period are frozen with the
    hash of its last operation and the PDF register is attached. An
    operation of a closed period can no longer be cancelled."""
    _name = 'pos.nm.exchange.register.closing'
    _inherit = ['mail.thread']
    _description = 'Exchange Register Closing'
    _order = 'date_stop desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Reference', required=True, readonly=True, default='/', copy=False)
    company_id = fields.Many2one('res.company', required=True, readonly=True, index=True,
                                 default=lambda self: self.env.company)
    office_id = fields.Many2one('pos.nm.exchange.office', string='Exchange Office', readonly=True,
                                check_company=True, help='Empty: every counter of the company.')
    date_start = fields.Datetime(string='From', required=True, readonly=True)
    date_stop = fields.Datetime(string='To', required=True, readonly=True)
    user_id = fields.Many2one('res.users', string='Closed By', readonly=True, default=lambda self: self.env.user)
    operation_count = fields.Integer(string='Operations', readonly=True)
    cancelled_count = fields.Integer(string='Cancelled', readonly=True)
    first_operation = fields.Char(string='First Reference', readonly=True)
    last_operation = fields.Char(string='Last Reference', readonly=True)
    last_hash = fields.Char(string='Hash of the Last Operation', readonly=True,
                            help='Register hash of the last operation of the company at closing: the operations '
                                 'up to it can be checked against this closing at any time.')
    integrity = fields.Char(string='Integrity', readonly=True,
                            help='Result of the integrity check of the register made at closing.')
    commission = fields.Monetary(string='Commissions', currency_field='currency_id', readonly=True)
    rate_margin = fields.Monetary(string='Rate Margins', currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    attachment_id = fields.Many2one('ir.attachment', string='Register (PDF)', readonly=True)

    @api.constrains('date_start', 'date_stop')
    def _check_dates(self):
        for closing in self:
            if closing.date_stop < closing.date_start:
                raise ValidationError(_("The end of the period must be after its start."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_closing(self):
        raise UserError(_("A closing of the exchange register cannot be deleted."))

    def write(self, vals):
        if not self.env.su and set(vals) - {'message_main_attachment_id'}:
            raise UserError(_("A closing of the exchange register cannot be changed."))
        return super().write(vals)

    @api.model
    def _nm_domain(self, company, office, date_start, date_stop):
        domain = [('company_id', '=', company.id), ('date', '>=', date_start), ('date', '<=', date_stop)]
        if office:
            domain.append(('office_id', '=', office.id))
        return domain

    @api.model
    def _nm_close(self, company, office, date_start, date_stop):
        """Close the register of ``office`` (else of ``company``) from
        ``date_start`` to ``date_stop`` (UTC datetimes)."""
        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise UserError(_("Only a Point of Sale manager can close the exchange register."))
        if date_stop > fields.Datetime.now():
            raise UserError(_("A period can only be closed once it is over."))
        overlap = self.sudo().search([
            ('company_id', '=', company.id),
            ('office_id', 'in', [office.id, False] if office else self.env['pos.nm.exchange.office'].sudo().search(
                [('company_id', '=', company.id)]).ids + [False]),
            ('date_start', '<=', date_stop), ('date_stop', '>=', date_start),
        ], limit=1)
        if overlap:
            raise UserError(_("The period overlaps the closing %(name)s (%(start)s - %(stop)s).",
                              name=overlap.name,
                              start=self.env['pos.nm.exchange']._nm_local_datetime(overlap.date_start),
                              stop=self.env['pos.nm.exchange']._nm_local_datetime(overlap.date_stop)))
        Exchange = self.env['pos.nm.exchange'].sudo()
        exchanges = Exchange.search(self._nm_domain(company, office, date_start, date_stop), order='id')
        open_sessions = exchanges.session_id.filtered(lambda s: s.state not in ('closed',))
        if open_sessions:
            raise UserError(_("Close the sessions of the period first: %s.", ', '.join(open_sessions.mapped('name'))))
        integrity = Exchange._nm_check_register_integrity(company)
        if integrity['broken']:
            raise UserError(_("The register cannot be closed: the operation %(name)s fails the integrity check "
                              "(%(reason)s).", name=integrity['broken'], reason=integrity['reason']))
        done = exchanges.filtered(lambda e: e.state == 'done')
        closing = self.sudo().create({
            'name': self.env['ir.sequence'].next_by_code('pos.nm.exchange.register.closing') or '/',
            'company_id': company.id,
            'office_id': office.id,
            'date_start': date_start,
            'date_stop': date_stop,
            'user_id': self.env.uid,
            'operation_count': len(exchanges),
            'cancelled_count': len(exchanges) - len(done),
            'first_operation': exchanges[:1].name or False,
            'last_operation': exchanges[-1:].name or False,
            'last_hash': integrity['last_hash'] or False,
            'integrity': _("%(count)s operations checked, chain intact up to %(last)s",
                           count=integrity['count'], last=integrity['last'] or '-'),
            'commission': sum(done.mapped('commission')),
            'rate_margin': sum(done.mapped('rate_margin')),
        })
        closing._nm_attach_register()
        return closing

    def _nm_report_data(self):
        self.ensure_one()
        offices = self.office_id
        configs = offices.config_ids if offices else self.env['pos.config']
        return {
            'date_start': fields.Datetime.to_string(self.date_start),
            'date_stop': fields.Datetime.to_string(self.date_stop),
            'config_ids': configs.ids,
            'office_id': self.office_id.id,
            'company_id': self.company_id.id,
            'closing_id': self.id,
        }

    def _nm_attach_register(self):
        self.ensure_one()
        report = self.env.ref('pos_nm_currency_exchange.action_report_exchange_register')
        pdf, _report_type = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
            report.report_name, res_ids=[], data=self._nm_report_data())
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f"{self.name.replace('/', '_')}.pdf",
            'type': 'binary',
            'raw': pdf,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        self.sudo().attachment_id = attachment
        self.sudo().message_post(body=_("Exchange register closed."), attachment_ids=attachment.ids)

    @api.model
    def _nm_closed_until(self, exchange):
        """Closing covering ``exchange``, else an empty recordset."""
        return self.sudo().search([
            ('company_id', '=', exchange.company_id.id),
            ('office_id', 'in', [exchange.office_id.id, False] if exchange.office_id else [False]),
            ('date_start', '<=', exchange.date), ('date_stop', '>=', exchange.date),
        ], limit=1)

    def action_download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }
