# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_pos_accounting import TestPosAccounting
from odoo.addons.pos_nm_currency_exchange.tests.test_exchange import TestPosCurrencyExchange


@tagged('post_install', '-at_install')
class TestPosCurrencyExchangeZeroDecimalMain(TestPosAccounting):
    """Exchange counter of a company in CFP francs (XPF, no decimals), with
    EUR in cash: 1 XPF = 0.008 EUR at the rate of Odoo (1 EUR = 125 XPF).

    EUR: 10% cash rate margin (buy rate 0.0088, 1 EUR bought 113.64 XPF),
    10% exchange sell margin (sell rate 0.008 / 1.1, 1 EUR sold 137.50 XPF),
    1 EUR coins, 2% commission, at least 100 XPF. The point of sale rounds
    the cash to 5 XPF coins.
    """

    @classmethod
    def setup_independent_company(cls, **kwargs):
        xpf = cls.env.ref('base.XPF')
        xpf.active = True
        return super().setup_independent_company(currency_id=xpf.id, **kwargs)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main = cls.company.currency_id
        cls.fx = cls.setup_other_currency('EUR', rates=[('1900-01-01', 0.008)])
        cls.cash_pm.currency_ids = [(4, cls.fx.id)]
        cls.commission_account = cls.env['account.account'].create({
            'name': 'EX Commissions', 'code': '999053', 'account_type': 'income_other'})
        rounding = cls.env['account.cash.rounding'].create({
            'name': '5 XPF', 'rounding': 5.0, 'rounding_method': 'HALF-UP', 'strategy': 'add_invoice_line',
            'profit_account_id': cls.company_data['default_account_revenue'].id,
            'loss_account_id': cls.company_data['default_account_expense'].id,
        })
        cls.pos_config.write({
            'cash_control': True,
            'cash_rounding': True,
            'rounding_method': rounding.id,
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': cls.commission_account.id,
            'nm_exchange_customer_threshold': 0.0,
        })
        cls.env['pos.nm.currency.setting'].create({
            'config_id': cls.pos_config.id,
            'currency_id': cls.fx.id,
            'margin_percent': 10.0,
            'exchange_sell_margin_percent': 10.0,
            'change_rounding': 1.0,
            'exchange_commission_percent': 2.0,
            'exchange_commission_min': 100.0,
        })

    _refresh_journal = TestPosCurrencyExchange._refresh_journal
    _open = TestPosCurrencyExchange._open
    _close = TestPosCurrencyExchange._close
    _quote = TestPosCurrencyExchange._quote

    def _commission_balance(self):
        lines = self.env['account.move.line'].search([('account_id', '=', self.commission_account.id)])
        return sum(lines.mapped('balance'))

    def test_quotes(self):
        """50 EUR at the buy rate are worth 5,681.82 -> 5,682 XPF; commission
        2%, 113.64 -> 114: 5,568 XPF, rounded down to the 5 XPF coins: 5,565
        handed back, commission 117. At the rate of Odoo the 50 EUR are
        worth 6,250: rate margin 568.

        10,000 XPF: commission 200, 9,800 x 0.008 / 1.1 = 71.27 EUR, rounded
        down to 71 EUR, worth 71 x 137.5 = 9,762.5 -> 9,763 XPF (rounded
        half up): commission 237; 71 EUR are worth 8,875 at the rate of
        Odoo, rate margin 888.

        1,000 XPF: commission 100 (the minimum), 900 x 0.008 / 1.1 = 6.55 EUR
        -> 6 EUR, worth 825 XPF: commission 175."""
        self.assertEqual(self.main.name, 'XPF')
        self.assertEqual(self.pos_config.currency_id, self.main)
        quote = self._quote(self.fx, 50.0, self.main)
        self.assertEqual(
            {key: quote[key] for key in ('amount_in', 'value_in', 'amount_out', 'value_out', 'commission',
                                         'rate_margin')},
            {'amount_in': 50.0, 'value_in': 5682.0, 'amount_out': 5565.0, 'value_out': 5565.0,
             'commission': 117.0, 'rate_margin': 568.0})
        quote = self._quote(self.main, 10000.0, self.fx)
        self.assertEqual(
            {key: quote[key] for key in ('amount_in', 'value_in', 'amount_out', 'value_out', 'commission',
                                         'rate_margin')},
            {'amount_in': 10000.0, 'value_in': 10000.0, 'amount_out': 71.0, 'value_out': 9763.0,
             'commission': 237.0, 'rate_margin': 888.0})
        quote = self._quote(self.main, 1000.0, self.fx)
        self.assertEqual((quote['amount_out'], quote['value_out'], quote['commission']), (6.0, 825.0, 175.0))
        # The amounts received in XPF have no decimals.
        self.assertEqual(self._quote(self.main, 1000.4, self.fx)['amount_in'], 1000.0)
        # The rate is given where it is at least 1, with the decimals of the rate.
        self.assertIn('1 EUR = ', self.env['pos.nm.exchange']._nm_rate_label(self.fx, self.main, 5565.0 / 50.0))
        self.assertIn('111.30', self.env['pos.nm.exchange']._nm_rate_label(self.fx, self.main, 5565.0 / 50.0))
        # Reverse quote: 5,565 XPF wanted take 50 EUR; one coin more, 51.
        Exchange = self.env['pos.nm.exchange']
        self.assertEqual(Exchange._nm_reverse_amount_in(self.pos_config, self.fx, self.main, 5565.0), 50.0)
        self.assertEqual(Exchange._nm_reverse_amount_in(self.pos_config, self.fx, self.main, 5566.0), 51.0)

    def test_operations_and_drawers(self):
        """Operations in XPF: integer statement lines, drawers checked in
        XPF and in EUR, commission posted in XPF."""
        session = self._open(fx=60.0, main=5000.0)
        Exchange = self.env['pos.nm.exchange']
        commission_before = self._commission_balance()
        # 5,565 XPF cannot be handed back from the 5,000 of the drawer.
        quote = Exchange.get_quote(self.pos_config.id, self.fx.id, 50.0, self.main.id)
        self.assertEqual(quote['drawer_balance_formatted'], self.main.format(5000.0))
        self.assertIn('cannot be handed back', quote['drawer_error'])
        with self.assertRaisesRegex(UserError, 'cannot be handed back'):
            Exchange.create_from_ui(session.id, self.fx.id, 50.0, self.main.id)
        # 10,000 XPF received, 71 EUR handed back from the 60 counted: refused.
        with self.assertRaisesRegex(UserError, 'cannot be handed back'):
            Exchange.create_from_ui(session.id, self.main.id, 10000.0, self.fx.id)
        # 44 EUR: 5,000 XPF at the buy rate, commission 100: 4,900 handed back.
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 44.0, self.main.id)['id'])
        self.assertEqual((exchange.value_in, exchange.amount_out, exchange.commission), (5000.0, 4900.0, 100.0))
        line_in, line_out = exchange.statement_line_in_id, exchange.statement_line_out_id
        self.assertEqual((line_in.foreign_currency_id, line_in.amount_currency, line_in.amount), (self.fx, 44.0, 5000.0))
        self.assertEqual(line_out.amount, -4900.0)
        self.assertEqual(session._nm_expected_cash(self.main), 100.0)
        self.assertEqual(session._nm_expected_cash(self.fx), 104.0)
        # 10,000 XPF: 71 EUR out of the 104.
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 10000.0, self.fx.id)['id'])
        self.assertEqual((exchange.amount_out, exchange.value_out, exchange.commission), (71.0, 9763.0, 237.0))
        self.assertEqual(exchange.statement_line_out_id.amount, -9763.0)
        self.assertEqual(session._nm_expected_cash(self.main), 10100.0)
        self.assertEqual(session._nm_expected_cash(self.fx), 33.0)
        self.assertEqual(self._commission_balance(), commission_before - 337.0)
        summary = session.get_closing_control_data()['nm_exchange_summary']
        self.assertEqual((summary['count'], summary['commission']), (2, 337.0))
        self._close(session, main=10100.0, fx=33.0)
        self.assertEqual(session.state, 'closed')
