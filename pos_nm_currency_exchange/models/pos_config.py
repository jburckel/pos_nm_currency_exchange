# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# Also set on the field of the settings: a related field does not copy the
# domain of its target.
EXCHANGE_INCOME_ACCOUNT_DOMAIN = [('account_type', 'in', ('income', 'income_other'))]


class PosConfig(models.Model):
    _inherit = 'pos.config'

    nm_exchange_enabled = fields.Boolean(
        string='Currency Exchange',
        default=True,
        help='Offer the currency exchange counter in the menu of the register: the customer '
             'brings notes in one cash currency of the point of sale and leaves with another.',
    )
    nm_exchange_income_account_id = fields.Many2one(
        'account.account',
        string='Exchange Commission Account',
        check_company=True,
        domain=EXCHANGE_INCOME_ACCOUNT_DOMAIN,
        help='Income account receiving the commissions of the exchange operations.',
    )
    nm_exchange_customer_threshold = fields.Monetary(
        string='Exchange Customer Required Above',
        currency_field='currency_id',
        help='Value of an exchange operation, in the currency of the point of sale, above which '
             'the customer must be identified. 0: never required. With a linked operations '
             'period, the value of the operations of the customer over that period is added.',
    )
    nm_exchange_customer_always = fields.Boolean(
        string='Exchange Customer Required for Every Operation',
        help='Every exchange operation names its customer, so that the operations of the same '
             'customer are added up over the linked operations period.',
    )
    nm_exchange_linked_days = fields.Integer(
        string='Exchange Linked Operations Period',
        help='Number of days over which the operations of a customer are linked: the value '
             'compared to the identification thresholds is the operation plus the operations of '
             'the customer over these days, at every point of sale of the company. 0: each '
             'operation alone.',
    )
    nm_exchange_document_threshold = fields.Monetary(
        string='Exchange Identity Document Required Above',
        currency_field='currency_id',
        help='Value, in the currency of the point of sale, above which the identity document of '
             'the customer is recorded on the operation (with the linked operations when a period '
             'is set). 0: never required.',
    )
    nm_exchange_count = fields.Integer(string='Exchanges', compute='_compute_nm_exchange_count')

    def _compute_nm_exchange_count(self):
        counts = dict(self.env['pos.nm.exchange']._read_group(
            [('config_id', 'in', self.ids), ('state', '=', 'done')], ['config_id'], ['__count']))
        for config in self:
            config.nm_exchange_count = counts.get(config, 0)

    @api.constrains('nm_exchange_customer_threshold', 'nm_exchange_document_threshold', 'nm_exchange_linked_days')
    def _check_nm_exchange_customer_threshold(self):
        for config in self:
            if config.nm_exchange_customer_threshold < 0 or config.nm_exchange_document_threshold < 0:
                raise ValidationError(_("The identification threshold cannot be negative."))
            if config.nm_exchange_linked_days < 0:
                raise ValidationError(_("The linked operations period cannot be negative."))

    @api.constrains('nm_exchange_income_account_id')
    def _check_nm_exchange_income_account(self):
        for config in self:
            account = config.nm_exchange_income_account_id
            if account and account.account_type not in ('income', 'income_other'):
                raise ValidationError(_("The exchange commission account must be an income account."))

    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if read_records:
            # The register tells the cashier why the counter cannot be used.
            read_records[0]['_nm_exchange_account_set'] = bool(config.nm_exchange_income_account_id)
        return read_records

    def _nm_exchange_currencies(self):
        """Currencies of the exchange counter: the currency of the point of
        sale and the foreign currencies of its cash payment method."""
        self.ensure_one()
        return self.currency_id | self._nm_get_foreign_cash_currencies()

    def _nm_odoo_rate(self, currency, date=None):
        """Units of ``currency`` for one unit of the POS currency at the rate
        of Odoo of the day, without any margin: the market value."""
        self.ensure_one()
        date = date or fields.Date.context_today(self)
        return self.env['res.currency']._get_conversion_rate(self.currency_id, currency, self.company_id, date)

    def _nm_exchange_sell_rate(self, currency):
        """Units of the foreign ``currency`` handed back by the exchange
        counter for one unit of the POS currency, always in favour of the
        counter.

        Rate of Odoo: the rate of Odoo less the exchange sell margin, the
        mirror of the cash rate of the notes received (the rate of Odoo plus
        the margin of POS Multi-Currency Cash).
        Fixed cash rate: the lower of the fixed rate and the fixed change
        rate, the lower rate handing back fewer notes.
        """
        self.ensure_one()
        setting = self._nm_get_currency_setting(currency)
        if setting.rate_mode == 'fixed':
            return min(setting.fixed_rate, setting.fixed_change_rate or setting.fixed_rate)
        return self._nm_odoo_rate(currency) / (1 + setting.exchange_sell_margin_percent / 100.0)

    def action_nm_view_exchanges(self):
        self.ensure_one()
        return {
            'name': _('Currency Exchanges'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.nm.exchange',
            'view_mode': 'list,form,pivot',
            'domain': [('config_id', '=', self.id)],
            # Like the count of the button: the cancelled operations are
            # one filter away.
            'context': {'default_config_id': self.id, 'search_default_done': 1},
        }
