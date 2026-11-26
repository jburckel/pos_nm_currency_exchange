# -*- coding: utf-8 -*-

import math

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.misc import formatLang

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
    nm_exchange_licence = fields.Char(
        string='Exchange License Number',
        help='License or registration number of the currency exchange activity, printed on the '
             'exchange receipts and the rate board when set.',
    )
    nm_exchange_count = fields.Integer(string='Exchanges', compute='_compute_nm_exchange_count')

    def _compute_nm_exchange_count(self):
        counts = dict(self.env['pos.nm.exchange']._read_group(
            [('config_id', 'in', self.ids), ('state', '=', 'done')], ['config_id'], ['__count']))
        for config in self:
            config.nm_exchange_count = counts.get(config, 0)

    def write(self, vals):
        # The POS users write the point of sale (from the register), but the
        # settings of the counter control them: identification thresholds,
        # commission account. Only the managers change them.
        if not self.env.su and any(name.startswith('nm_exchange_') for name in vals) \
                and not self.env.user.has_group('point_of_sale.group_pos_manager') \
                and not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Only a Point of Sale manager can change the settings of the currency exchange "
                                "counter."))
        return super().write(vals)

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
            read_records[0]['_nm_id_document_types'] = self.env['pos.nm.exchange']._fields[
                'id_document_type']._description_selection(self.env)
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

        Rate of Odoo: the rate of Odoo divided by 1 + the exchange sell margin, the
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

    def _nm_board_amount(self, currency):
        """Typical amount of ``currency`` on the rate board: the power of 10
        nearest to 100 units of the currency of the point of sale (100 USD,
        10,000 XPF, 1,000,000 VND), rounded to the nearest amount the counter
        takes and hands back as is: a multiple of the payment step of the
        currency (the notes received) and of its change step (the notes
        handed back), the steps of the quote. With 3 CHF coins, 99 CHF."""
        self.ensure_one()
        rate = self._nm_odoo_rate(currency)
        amount = 10.0 ** max(0, round(math.log10(100 * rate))) if rate > 0 else 100.0
        Exchange = self.env['pos.nm.exchange']
        # Both steps in units of the rounding of the currency: their least
        # common multiple is the smallest amount that is a multiple of both.
        units = math.lcm(*(
            max(1, round(step / currency.rounding))
            for step in (Exchange._nm_payment_step(self, currency), Exchange._nm_change_step(self, currency))))
        step = units * currency.rounding
        return currency.round(max(1, round(amount / step)) * step)

    def _nm_format_percent(self, percent):
        """``percent`` with its 4 decimals at most, without trailing zeros
        beyond the second one (0.125, 2.50)."""
        digits = 4
        while digits > 2 and round(percent, digits - 1) == round(percent, digits):
            digits -= 1
        return formatLang(self.env, percent, digits=digits)

    def _nm_rate_board(self):
        """Exchange rates of the counter shown to the customers, for each
        foreign cash currency, computed by the quote of the counter so that
        they match the operations exactly:

        - we buy: value of 1 unit of the notes received (cash rate, before
          the commission) and amount handed back for the typical amount;
        - we sell: price of 1 unit of the notes handed back (sell rate,
          before the commission) and amount to pay for the typical amount
          (reverse quote);
        - the commission rule of the currency.
        """
        self.ensure_one()
        Exchange = self.env['pos.nm.exchange']
        main = self.currency_id
        rows = []
        for currency in self._nm_get_foreign_cash_currencies().sorted('name'):
            amount = self._nm_board_amount(currency)
            buy_unit = 1.0 / self._nm_cash_rate(currency)
            sell_unit = 1.0 / self._nm_exchange_sell_rate(currency)
            buy_amount = Exchange._nm_quote(self, currency, amount, main)['amount_out']
            sell_amount = Exchange._nm_reverse_amount_in(self, main, currency, amount)
            setting = self._nm_get_currency_setting(currency)
            rows.append({
                'currency': currency.name,
                'currency_id': currency.id,
                'amount': amount,
                'amount_formatted': currency.format(amount),
                'buy_unit': buy_unit,
                'buy_rate_label': Exchange._nm_rate_label(currency, main, buy_unit),
                'buy_amount': buy_amount,
                'buy_amount_formatted': main.format(buy_amount),
                'sell_unit': sell_unit,
                'sell_rate_label': Exchange._nm_rate_label(currency, main, sell_unit),
                'sell_amount': sell_amount,
                'sell_amount_formatted': main.format(sell_amount),
                'commission_label': self._nm_commission_label(setting),
            })
        return {
            'config_name': self.name,
            'licence': self.nm_exchange_licence or '',
            'date': Exchange._nm_local_datetime(fields.Datetime.now()),
            'currency': main.name,
            'rows': rows,
        }

    def _nm_commission_label(self, setting):
        """Commission rule of a currency in one translatable sentence,
        without the parts that are zero: '2.00 % + $ 1.00, min. $ 3.00',
        '1.50 %, min. $ 2.00', 'No commission'."""
        main = self.currency_id
        values = {
            'percent': self._nm_format_percent(setting.exchange_commission_percent),
            'fixed': main.format(setting.exchange_commission_fixed),
            'min': main.format(setting.exchange_commission_min),
        }
        labels = {
            (True, True, True): _("%(percent)s %% + %(fixed)s, min. %(min)s", **values),
            (True, True, False): _("%(percent)s %% + %(fixed)s", **values),
            (True, False, True): _("%(percent)s %%, min. %(min)s", **values),
            (True, False, False): _("%(percent)s %%", **values),
            (False, True, True): _("%(fixed)s, min. %(min)s", **values),
            (False, True, False): values['fixed'],
            (False, False, True): _("Min. %(min)s", **values),
            (False, False, False): _("No commission"),
        }
        return labels[(
            bool(setting.exchange_commission_percent),
            not main.is_zero(setting.exchange_commission_fixed),
            not main.is_zero(setting.exchange_commission_min),
        )]

    def action_nm_print_rate_board(self):
        return self.env.ref('pos_nm_currency_exchange.action_report_exchange_rates').report_action(self)

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
