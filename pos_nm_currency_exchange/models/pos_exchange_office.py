# -*- coding: utf-8 -*-

from uuid import uuid4

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

# Settings of a currency copied from the reference counter to the other
# counters of an office, everything that makes the amount a customer gets:
# the cash rate of POS Multi-Currency Cash (the buy rate), the coins and
# notes taken and handed back, the sell margin and the commissions. The
# closing difference a cashier may validate stays per counter.
SYNCED_SETTING_FIELDS = (
    'rate_mode', 'fixed_rate', 'fixed_change_rate', 'margin_percent',
    'change_rounding', 'change_rest_mode', 'payment_rounding',
    'exchange_sell_margin_percent', 'exchange_commission_percent', 'exchange_commission_fixed',
    'exchange_commission_min',
)

# Rules of the counter: shared by the counters of an office (fields of the
# office), else read on the point of sale. Key of the rule: field of the
# office, field of the point of sale.
RULE_FIELDS = {
    'licence': ('licence', 'nm_exchange_licence'),
    'customer_threshold': ('customer_threshold', 'nm_exchange_customer_threshold'),
    'customer_always': ('customer_always', 'nm_exchange_customer_always'),
    'document_threshold': ('document_threshold', 'nm_exchange_document_threshold'),
    'linked_days': ('linked_days', 'nm_exchange_linked_days'),
    'origin_threshold': ('origin_threshold', 'nm_exchange_origin_threshold'),
    'review_threshold': ('review_threshold', 'nm_exchange_review_threshold'),
}


class PosNmExchangeOffice(models.Model):
    """Exchange office: the counters (points of sale) of one licensed
    place of business. They share the licence, the identification and
    review rules and, with Apply to the Counters, the rates and
    commissions of the reference counter."""
    _name = 'pos.nm.exchange.office'
    _inherit = ['mail.thread']
    _description = 'Exchange Office'
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')
    partner_id = fields.Many2one(
        'res.partner', string='Address', check_company=True,
        help='Address of the office, printed on the exchange register and the rate board.')
    licence = fields.Char(
        string='Exchange Licence Number', tracking=True,
        help='Licence or registration number of the office, printed on the receipts, the rate board and the '
             'exchange register of its counters.')
    compliance_user_id = fields.Many2one(
        'res.users', string='Compliance Officer', tracking=True,
        domain=[('share', '=', False)],
        help='Receives an activity for every operation flagged To Review at the counters of the office.')
    config_ids = fields.One2many('pos.config', 'nm_exchange_office_id', string='Counters')
    config_count = fields.Integer(string='Counter Count', compute='_compute_config_count')
    reference_config_id = fields.Many2one(
        'pos.config', string='Reference Counter', check_company=True,
        domain="[('nm_exchange_office_id', '=', id)]",
        help='Counter whose rates and commissions Apply to the Counters copies to the other counters, and whose '
             'rates the board of the office shows.')

    customer_threshold = fields.Monetary(
        string='Customer Required Above', currency_field='currency_id', tracking=True,
        help='Value of an operation, in the currency of the company, above which the customer must be '
             'identified. 0: never required.')
    customer_always = fields.Boolean(
        string='Customer Required for Every Operation', tracking=True)
    document_threshold = fields.Monetary(
        string='Identity Document Required Above', currency_field='currency_id', tracking=True,
        help='Value above which the identity document of the customer is recorded on the operation. '
             '0: never required.')
    origin_threshold = fields.Monetary(
        string='Origin of Funds Required Above', currency_field='currency_id', tracking=True,
        help='Value above which the customer declares the origin of the funds. 0: never required.')
    review_threshold = fields.Monetary(
        string='Review Above', currency_field='currency_id', tracking=True,
        help='Value above which the operation is flagged To Review for the compliance officer. It is never '
             'refused at the counter. 0: never flagged.')
    linked_days = fields.Integer(
        string='Linked Operations Period', tracking=True,
        help='Number of days over which the operations of a customer are added up before they are compared to '
             'the thresholds, at every point of sale of the company. 0: each operation alone.')

    board_token = fields.Char(
        string='Board Access Token', copy=False, default=lambda self: uuid4().hex,
        groups='point_of_sale.group_pos_manager',
        help='Secret part of the address of the rate board of the office.')
    board_url = fields.Char(string='Rate Board Address', compute='_compute_board_url',
                            groups='point_of_sale.group_pos_manager')
    board_refresh = fields.Integer(
        string='Board Refresh (seconds)', default=60,
        help='The rate board reloads the rates every so many seconds.')

    @api.depends('config_ids')
    def _compute_config_count(self):
        for office in self:
            office.config_count = len(office.config_ids)

    @api.depends('board_token')
    def _compute_board_url(self):
        base = self.get_base_url()
        for office in self:
            office.board_url = (
                f"{base}/pos_nm_exchange/office_board/{office.id}?access_token={office.board_token}"
                if office.id and office.board_token else False)

    @api.constrains('customer_threshold', 'document_threshold', 'origin_threshold', 'review_threshold',
                    'linked_days', 'board_refresh')
    def _check_rules(self):
        for office in self:
            if min(office.customer_threshold, office.document_threshold, office.origin_threshold,
                   office.review_threshold) < 0:
                raise ValidationError(_("The identification threshold cannot be negative."))
            if office.linked_days < 0:
                raise ValidationError(_("The linked operations period cannot be negative."))
            if office.board_refresh and office.board_refresh < 10:
                raise ValidationError(_("The rate board cannot reload the rates more often than every 10 seconds."))

    @api.constrains('reference_config_id', 'config_ids')
    def _check_reference_config(self):
        for office in self:
            if office.reference_config_id and office.reference_config_id not in office.config_ids:
                raise ValidationError(_("The reference counter must be a counter of the office."))

    def _nm_rules(self):
        self.ensure_one()
        return {rule: self[office_field] for rule, (office_field, _config_field) in RULE_FIELDS.items()}

    def _nm_reference_config(self):
        """Counter whose rates the office applies and shows."""
        self.ensure_one()
        return self.reference_config_id or self.config_ids.filtered('nm_exchange_enabled')[:1] or self.config_ids[:1]

    # ------------------------------------------------------------------
    # Same rates at every counter
    # ------------------------------------------------------------------

    def _nm_rate_differences(self):
        """Settings of the counters that differ from the reference counter:
        a list of dicts (counter, currency, field label, reference value,
        value of the counter). A currency of the reference counter missing
        on a counter is reported once, field False."""
        self.ensure_one()
        reference = self._nm_reference_config()
        differences = []
        if not reference:
            return differences
        Setting = self.env['pos.nm.currency.setting']
        for config in self.config_ids - reference:
            for ref_setting in Setting.search([('config_id', '=', reference.id)]):
                setting = config._nm_get_currency_setting(ref_setting.currency_id)
                if not setting:
                    differences.append({
                        'config': config.name, 'currency': ref_setting.currency_id.name, 'field': False,
                        'reference': '', 'value': '',
                    })
                    continue
                for name in SYNCED_SETTING_FIELDS:
                    if ref_setting[name] != setting[name]:
                        differences.append({
                            'config': config.name, 'currency': ref_setting.currency_id.name,
                            'field': Setting._fields[name].get_description(self.env)['string'],
                            'reference': ref_setting[name], 'value': setting[name],
                        })
        return differences

    def action_nm_apply_rates(self):
        """Copy the rates and commissions of every currency of the reference
        counter to the other counters of the office that accept that
        currency (logged in the chatter of each setting)."""
        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise UserError(_("Only a Point of Sale manager can change the rates of the counters."))
        Setting = self.env['pos.nm.currency.setting']
        skipped = []
        for office in self:
            reference = office._nm_reference_config()
            if not reference:
                raise UserError(_("The office %s has no counter.", office.name))
            for ref_setting in Setting.search([('config_id', '=', reference.id)]):
                values = {name: ref_setting[name] for name in SYNCED_SETTING_FIELDS}
                for config in office.config_ids - reference:
                    if ref_setting.currency_id not in config._nm_get_foreign_cash_currencies():
                        skipped.append(f"{config.name} ({ref_setting.currency_id.name})")
                        continue
                    setting = config._nm_get_currency_setting(ref_setting.currency_id)
                    if setting:
                        changed = {name: value for name, value in values.items() if setting[name] != value}
                        if changed:
                            setting.write(changed)
                    else:
                        Setting.create({'config_id': config.id, 'currency_id': ref_setting.currency_id.id, **values})
            office.message_post(body=_("Rates and commissions of %s applied to the counters.", reference.name))
        if skipped:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'sticky': True,
                    'message': _("Applied. These counters do not accept the currency in their cash payment method: %s",
                                 ', '.join(skipped)),
                },
            }
        return True

    def action_nm_view_rate_differences(self):
        self.ensure_one()
        differences = self._nm_rate_differences()
        if not differences:
            message = _("Every counter of the office uses the rates and commissions of the reference counter.")
            kind = 'success'
        else:
            lines = [
                _("%(config)s, %(currency)s: not set", **d) if not d['field'] else
                _("%(config)s, %(currency)s, %(field)s: %(value)s instead of %(reference)s", **d)
                for d in differences]
            message = '\n'.join(lines)
            kind = 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'type': kind, 'sticky': bool(differences), 'message': message},
        }

    def action_nm_regenerate_board_token(self):
        for office in self:
            office.board_token = uuid4().hex
        return True

    def action_nm_open_board(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.board_url, 'target': 'new'}

    def action_nm_view_configs(self):
        self.ensure_one()
        return {
            'name': _('Counters'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.config',
            'view_mode': 'list,form',
            'domain': [('nm_exchange_office_id', '=', self.id)],
            'context': {'default_nm_exchange_office_id': self.id},
        }

    def action_nm_view_exchanges(self):
        self.ensure_one()
        return {
            'name': _('Currency Exchanges'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.nm.exchange',
            'view_mode': 'list,form,pivot',
            'domain': [('office_id', '=', self.id)],
            'context': {'search_default_done': 1},
        }

    def _nm_rate_board(self):
        """Rate board of the office: the board of its reference counter,
        under the name, address and licence of the office."""
        self.ensure_one()
        config = self._nm_reference_config()
        if not config:
            raise UserError(_("The office %s has no counter.", self.name))
        board = config._nm_rate_board()
        board.update({
            'config_name': self.name,
            'licence': self.licence or '',
            'address': self.partner_id._display_address(without_name=True).replace('\n', ', ')
            if self.partner_id else '',
        })
        return board
