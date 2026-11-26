# -*- coding: utf-8 -*-

from datetime import datetime

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PosNmExchangeRegisterWizard(models.TransientModel):
    _name = 'pos.nm.exchange.register.wizard'
    _description = 'Print the Exchange Register'

    def _default_date_start(self):
        """Start of the current month in the time zone of the user."""
        tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        start = datetime.now(tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        return tz.localize(start).astimezone(pytz.utc).replace(tzinfo=None)

    date_start = fields.Datetime(string='From', required=True, default=_default_date_start,
                                 help='Operations recorded from this date and time.')
    date_stop = fields.Datetime(string='To', required=True, default=fields.Datetime.now,
                                help='Operations recorded up to this date and time.')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    office_id = fields.Many2one(
        'pos.nm.exchange.office', string='Exchange Office', domain="[('company_id', '=', company_id)]",
        help='Operations of the counters of this office; empty: the points of sale below.')
    config_ids = fields.Many2many(
        'pos.config', string='Points of Sale',
        help='Points of sale of the register; all of them when empty.')

    @api.constrains('date_start', 'date_stop')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_stop < wizard.date_start:
                raise ValidationError(_("The end of the period must be after its start."))

    def _nm_report_data(self):
        self.ensure_one()
        return {
            'date_start': fields.Datetime.to_string(self.date_start),
            'date_stop': fields.Datetime.to_string(self.date_stop),
            'config_ids': self.config_ids.ids,
            'office_id': self.office_id.id,
            'company_id': self.company_id.id,
        }

    def action_close_period(self):
        """Close the register of the period: figures and hash frozen, PDF
        attached (pos.nm.exchange.register.closing)."""
        self.ensure_one()
        if self.config_ids and not self.office_id:
            raise UserError(_("The register is closed for an exchange office or for the whole company: clear the "
                              "points of sale."))
        closing = self.env['pos.nm.exchange.register.closing']._nm_close(
            self.company_id, self.office_id, self.date_start, self.date_stop)
        return {
            'type': 'ir.actions.act_window',
            'res_model': closing._name,
            'res_id': closing.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_check_integrity(self):
        self.ensure_one()
        result = self.env['pos.nm.exchange']._nm_check_register_integrity(self.company_id)
        if result['broken']:
            message = _("Integrity check failed at %(name)s: %(reason)s.", name=result['broken'],
                        reason=result['reason'])
            kind = 'danger'
        else:
            message = _("%(count)s operations checked: the register is intact (last: %(last)s).",
                        count=result['count'], last=result['last'] or '-')
            if result['unhashed']:
                message += ' ' + _("%s older operations were recorded before the hash chain.", result['unhashed'])
            kind = 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'type': kind, 'sticky': kind == 'danger', 'message': message},
        }

    def action_print(self):
        return self.env.ref('pos_nm_currency_exchange.action_report_exchange_register').report_action(
            [], data=self._nm_report_data())
