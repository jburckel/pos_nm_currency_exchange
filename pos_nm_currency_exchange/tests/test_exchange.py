# -*- coding: utf-8 -*-

from datetime import timedelta
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger
from odoo.addons.point_of_sale.tests.test_pos_accounting import TestPosAccounting


@tagged('post_install', '-at_install')
class TestPosCurrencyExchange(TestPosAccounting):
    """Exchange counter on the drawers of pos_nm_multicurrencies.

    ``setup_other_currency``: 1 company currency = 2 foreign units at the
    latest rate of Odoo. The counter buys the notes at the cash rate, 2 x 1.1
    = 2.2 (10% cash rate margin), and sells them at 2 / 1.1 = 1.818181...
    (10% exchange sell margin).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fx = cls.setup_other_currency('EUR')
        cls.main = cls.company.currency_id
        cls.cash_pm.currency_ids = [(4, cls.fx.id)]
        cls.profit_account = cls.env['account.account'].create({
            'name': 'EX Cash Profit', 'code': '999051', 'account_type': 'income_other'})
        cls.loss_account = cls.env['account.account'].create({
            'name': 'EX Cash Loss', 'code': '999052', 'account_type': 'expense'})
        cls.commission_account = cls.env['account.account'].create({
            'name': 'EX Commissions', 'code': '999053', 'account_type': 'income_other'})
        cls.cash_journal.write({'profit_account_id': cls.profit_account.id, 'loss_account_id': cls.loss_account.id})
        cls.pos_config.write({
            'cash_control': True,
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': cls.commission_account.id,
            'nm_exchange_customer_threshold': 0.0,
        })
        cls.setting = cls.env['pos.nm.currency.setting'].create({
            'config_id': cls.pos_config.id,
            'currency_id': cls.fx.id,
            'margin_percent': 10.0,
            'exchange_sell_margin_percent': 10.0,
            'change_rounding': 1.0,
            'exchange_commission_percent': 2.0,
            'exchange_commission_fixed': 1.0,
            'exchange_commission_min': 3.0,
        })
        cls.partner_id = cls.env.user.partner_id.id
        cls.pos_user = new_test_user(
            cls.env, login='nm_exchange_cashier', name='NM Cashier', groups='point_of_sale.group_pos_user',
            company_id=cls.company.id)

    def _refresh_journal(self):
        self.cash_journal.invalidate_recordset(['current_statement_balance', 'has_statement_lines'])

    def _open(self, fx=0.0, main=0.0, counts=None):
        """Open a session with ``main`` in the main drawer, ``fx`` in the EUR
        drawer and ``counts`` ({currency: amount}) in the other drawers."""
        self._refresh_journal()
        self.pos_config.open_ui()
        session = self.get_pos_session()
        session.set_multicurrency_counts({
            str(self.fx.id): fx, **{str(currency.id): amount for currency, amount in (counts or {}).items()}})
        session.set_opening_control(main, '')
        session.bank_statement_id.flush_recordset()
        return session

    def _close(self, session, main=0.0, fx=0.0):
        self._refresh_journal()
        session.set_multicurrency_counts({self.fx.id: fx})
        result = session.close_session_from_ui({self.cash_pm.id: main})
        self.assertTrue(result['status'], result)

    def _quote(self, currency_in, amount_in, currency_out):
        return self.env['pos.nm.exchange']._nm_quote(self.pos_config, currency_in, amount_in, currency_out)

    def _add_cash_currency(self, code, rate, **setting_vals):
        """Another foreign cash currency, ``rate`` units for 1 company
        currency at the rate of Odoo, with its own setting."""
        currency = self.setup_other_currency(code, rates=[('1900-01-01', rate)])
        self.cash_pm.currency_ids = [(4, currency.id)]
        self.env['pos.nm.currency.setting'].create({
            'config_id': self.pos_config.id, 'currency_id': currency.id, **setting_vals})
        return currency

    # ------------------------------------------------------------------

    def test_setting_constraints(self):
        with self.assertRaises(ValidationError):
            self.setting.exchange_commission_percent = -1
        with self.assertRaises(ValidationError):
            self.setting.exchange_commission_percent = 100
        with self.assertRaises(ValidationError):
            self.pos_config.nm_exchange_customer_threshold = -1
        with self.assertRaises(ValidationError):
            self.setting.exchange_sell_margin_percent = -1
        self.assertEqual(self.setting._nm_exchange_commission(100.0), 3.0)   # 2 + 1, at least 3
        self.assertEqual(self.setting._nm_exchange_commission(1000.0), 21.0)  # 20 + 1
        self.assertEqual(self.setting._nm_exchange_commission(50.0), 3.0)    # 1 + 1 = 2: the minimum 3 wins
        # The sell margin is logged like the rates.
        before = len(self.setting.message_ids)
        self.setting.exchange_sell_margin_percent = 12.0
        self.assertEqual(len(self.setting.message_ids), before + 1)
        self.setting.exchange_sell_margin_percent = 10.0
        # Every change of the commissions is logged like the rates.
        before = len(self.setting.message_ids)
        self.setting.exchange_commission_percent = 2.5
        self.assertEqual(len(self.setting.message_ids), before + 1)
        self.setting.exchange_commission_percent = 2.0
        # The fields logged by the parent module still are.
        before = len(self.setting.message_ids)
        self.setting.change_rest_mode = 'main'
        self.assertEqual(len(self.setting.message_ids), before + 1)
        self.setting.change_rest_mode = 'rounding'

    def test_quote_main_to_foreign(self):
        """100 main received: commission 3, 97 to hand back = 176.36 EUR at
        the sell rate 2 / 1.1, rounded down to the 1 EUR note: 176 EUR worth
        176 x 1.1 / 2 = 96.80, commission 3.20. At the rate of Odoo the 176
        EUR are worth 88: the counter earns 96.80 - 88 = 8.80 on the rate,
        12 in all for 100 main (the margin given away before: 213 EUR, worth
        106.50, were handed back for 100 main)."""
        quote = self._quote(self.main, 100.0, self.fx)
        self.assertEqual(quote['value_in'], 100.0)
        self.assertEqual(quote['amount_out'], 176.0)
        self.assertEqual(quote['value_out'], 96.8)
        self.assertEqual(quote['commission'], 3.2)
        self.assertEqual(quote['rate_margin'], 8.8)
        self.assertAlmostEqual(quote['rate'], 1.76, places=6)

    def test_quote_foreign_to_main(self):
        """220 EUR received at the cash rate 2.2: worth 100, commission 3,
        97 handed back in the main currency. At the rate of Odoo the 220 EUR
        are worth 110: rate margin 10."""
        quote = self._quote(self.fx, 220.0, self.main)
        self.assertEqual(quote['value_in'], 100.0)
        self.assertEqual(quote['commission'], 3.0)
        self.assertEqual(quote['amount_out'], 97.0)
        self.assertEqual(quote['value_out'], 97.0)
        self.assertEqual(quote['rate_margin'], 10.0)
        self.assertAlmostEqual(quote['rate'], 97.0 / 220.0, places=6)

    def test_quote_spread_favours_the_counter(self):
        """Whatever the direction and the amount: the notes handed back are
        never worth more at the rate of Odoo than their booked value, the
        notes received never less, the commission never falls below the
        configured one, and commission plus rate margin is the difference of
        the market values."""
        Exchange = self.env['pos.nm.exchange']
        for currency_in, currency_out in ((self.main, self.fx), (self.fx, self.main)):
            for amount_in in (7.0, 40.0, 99.99, 100.0, 1234.56, 5000.01):
                quote = self._quote(currency_in, amount_in, currency_out)
                market_in = Exchange._nm_market_value(self.pos_config, currency_in, quote['amount_in'])
                market_out = Exchange._nm_market_value(self.pos_config, currency_out, quote['amount_out'])
                self.assertLessEqual(self.main.compare_amounts(market_out, quote['value_out']), 0)
                self.assertGreaterEqual(self.main.compare_amounts(market_in, quote['value_in']), 0)
                self.assertGreaterEqual(
                    self.main.compare_amounts(quote['commission'], self.setting._nm_exchange_commission(
                        quote['value_in'])), 0)
                self.assertAlmostEqual(quote['commission'] + quote['rate_margin'], market_in - market_out, places=2)

    def test_quote_sell_margin_zero(self):
        """Sell margin 0: the notes are handed back at the rate of Odoo,
        97 x 2 = 194 EUR, worth exactly 97: no rate margin on that side."""
        self.setting.exchange_sell_margin_percent = 0.0
        quote = self._quote(self.main, 100.0, self.fx)
        self.assertEqual(quote['amount_out'], 194.0)
        self.assertEqual(quote['value_out'], 97.0)
        self.assertEqual(quote['commission'], 3.0)
        self.assertEqual(quote['rate_margin'], 0.0)

    def test_quote_never_negative(self):
        """No commission at all, no rounding step, no margin: the notes are
        rounded down, so the commission is never negative."""
        self.setting.write({
            'margin_percent': 0.0, 'exchange_sell_margin_percent': 0.0, 'change_rounding': 0.0,
            'exchange_commission_percent': 0.0, 'exchange_commission_fixed': 0.0, 'exchange_commission_min': 0.0,
        })
        self.setup_other_currency('EUR', rates=[('1900-01-01', 0.8373)])
        for cents in range(1, 400, 7):
            for currency_in, currency_out in ((self.main, self.fx), (self.fx, self.main)):
                quote = self._quote(currency_in, cents / 100.0, currency_out)
                self.assertGreaterEqual(quote['commission'], 0.0, quote)
                self.assertGreaterEqual(quote['rate_margin'], 0.0, quote)

    def test_quote_fixed_change_rate(self):
        """Fixed cash rate: the notes received at the fixed rate, the notes
        handed back at the lower of the fixed rate and the fixed change rate,
        the sell margin is not used."""
        self.setting.write({'rate_mode': 'fixed', 'fixed_rate': 2.5, 'fixed_change_rate': 2.4})
        quote = self._quote(self.fx, 250.0, self.main)
        self.assertEqual(quote['value_in'], 100.0)
        # 250 EUR are worth 125 at the rate of Odoo: 25 earned on the rate.
        self.assertEqual(quote['rate_margin'], 25.0)
        quote = self._quote(self.main, 100.0, self.fx)
        self.assertEqual(quote['amount_out'], 232.0)  # 97 x 2.4 = 232.8 -> 232
        self.assertEqual(quote['value_out'], 96.67)
        # Fixed rates above the rate of Odoo (2): the 232 EUR are worth 116,
        # the rate margin shows the loss, 96.67 - 116.
        self.assertEqual(quote['rate_margin'], -19.33)
        # A change rate above the fixed rate would hand back more notes: the
        # fixed rate is used.
        self.setting.fixed_change_rate = 2.6
        quote = self._quote(self.main, 100.0, self.fx)
        self.assertEqual(quote['amount_out'], 242.0)  # 97 x 2.5 = 242.5 -> 242
        self.assertEqual(quote['value_out'], 96.8)
        self.setting.write({'rate_mode': 'odoo', 'fixed_rate': 0.0, 'fixed_change_rate': 0.0})

    def test_quote_pos_cash_rounding(self):
        """Notes handed back in the currency of the point of sale: rounded
        down to its cash rounding. 221 EUR are worth 100.45; commission
        2.009 + 1 = 3.01; 97.44 rounded down to 0.05 = 97.40, so the
        commission is 3.05."""
        rounding = self.env['account.cash.rounding'].create({
            'name': 'NM 0.05', 'rounding': 0.05, 'rounding_method': 'HALF-UP',
            'profit_account_id': self.profit_account.id, 'loss_account_id': self.loss_account.id})
        self.pos_config.write({'cash_rounding': True, 'rounding_method': rounding.id})
        quote = self._quote(self.fx, 221.0, self.main)
        self.assertEqual(quote['value_in'], 100.45)
        self.assertEqual(quote['amount_out'], 97.4)
        self.assertEqual(quote['value_out'], 97.4)
        self.assertEqual(quote['commission'], 3.05)
        # The EUR notes handed back keep their own change rounding.
        self.assertEqual(self._quote(self.main, 100.0, self.fx)['amount_out'], 176.0)

    def test_rate_label(self):
        """The rate is shown in the direction where it is at least 1, with 2 to
        4 decimals whatever the currencies: 0.0084 USD for 1 XPF is not
        "$ 0.01" but "1 USD = 119.05 XPF"."""
        Exchange = self.env['pos.nm.exchange']
        xpf = self.env.ref('base.XPF')
        label = Exchange._nm_rate_label(xpf, self.main, 1 / 119.05)
        self.assertIn('1 %s = ' % self.main.name, label)
        self.assertIn('119.05', label)
        self.assertIn(xpf.symbol, label)
        # 2.13 EUR for 1: kept as is, without trailing zeros.
        label = Exchange._nm_rate_label(self.main, self.fx, 2.13)
        self.assertIn('1 %s = ' % self.main.name, label)
        self.assertIn('2.13', label)
        self.assertNotIn('2.130', label)
        # 97 for 220 EUR: 1 main = 2.268 EUR (3 decimals are enough).
        label = Exchange._nm_rate_label(self.fx, self.main, 97.0 / 220.0)
        self.assertIn('1 %s = ' % self.main.name, label)
        self.assertIn('2.268', label)
        self.assertNotIn('2.2680', label)
        self.assertEqual(Exchange._nm_rate_label(self.fx, self.main, 0.0), '-')

    def test_get_quote_rpc(self):
        quote = self.env['pos.nm.exchange'].get_quote(self.pos_config.id, self.main.id, 100.0, self.fx.id)
        self.assertEqual(quote['amount_out'], 176.0)
        self.assertIn('176', quote['amount_out_formatted'])
        self.assertIn('rate_label', quote)
        with self.assertRaises(UserError):
            self.env['pos.nm.exchange'].get_quote(self.pos_config.id, self.main.id, 100.0, self.main.id)
        with self.assertRaises(UserError):
            self.env['pos.nm.exchange'].get_quote(self.pos_config.id, self.main.id, -5.0, self.fx.id)
        # Nothing left to hand back once the commission is deducted.
        with self.assertRaisesRegex(UserError, 'too small'):
            self.env['pos.nm.exchange'].get_quote(self.pos_config.id, self.main.id, 3.0, self.fx.id)
        gbp = self.env.ref('base.GBP')
        gbp.active = True
        with self.assertRaises(UserError):
            self.env['pos.nm.exchange'].get_quote(self.pos_config.id, self.main.id, 100.0, gbp.id)

    def test_exchange_operation(self):
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, False, 'tourist')
        exchange = Exchange.browse(receipt['id'])
        self.assertTrue(exchange.name.startswith('EXC/'))
        self.assertEqual(exchange.state, 'done')
        self.assertEqual(exchange.session_id, session)
        self.assertEqual(exchange.config_id, self.pos_config)
        self.assertEqual(exchange.user_id, self.env.user)
        self.assertEqual(exchange.cashier_name, self.env.user.name)
        self.assertEqual(exchange.note, 'tourist')
        self.assertEqual(exchange.amount_in, 100.0)
        self.assertEqual(exchange.amount_out, 176.0)
        self.assertEqual(exchange.commission, 3.2)
        self.assertEqual(exchange.rate_margin, 8.8)
        self.assertIn('176', receipt['amount_out'])
        self.assertEqual(receipt['rate_label'], exchange.rate_label)
        self.assertIn('1.76', exchange.rate_label)
        self.assertEqual(receipt['cashier_name'], self.env.user.name)

        line_in = exchange.statement_line_in_id
        line_out = exchange.statement_line_out_id
        self.assertEqual(line_in.amount, 100.0)
        self.assertFalse(line_in.foreign_currency_id)
        self.assertEqual(line_in.pos_session_id, session)
        self.assertEqual(line_out.amount, -96.8)
        self.assertEqual(line_out.foreign_currency_id, self.fx)
        self.assertEqual(line_out.amount_currency, -176.0)
        for line in (line_in, line_out):
            self.assertIn(self.commission_account, line.move_id.line_ids.account_id)
        commission_lines = (line_in.move_id.line_ids + line_out.move_id.line_ids).filtered(
            lambda l: l.account_id == self.commission_account)
        self.assertEqual(self.main.round(-sum(commission_lines.mapped('balance'))), 3.2)

        # Drawers: 176 EUR left the foreign drawer, 100 entered the main one.
        self.assertEqual(self.pos_config._nm_currency_balance(self.fx), 324.0)
        detail = session.currency_detail_ids.filtered(lambda d: d.currency_id == self.fx)
        self.assertEqual(detail.cash_moves_amount, -176.0)
        self._refresh_journal()
        data = session.get_closing_control_data()
        fx_data = next(d for d in data['multicurrency_details'] if d['currency_id'] == self.fx.id)
        self.assertEqual(fx_data['amount'], 324.0)
        self.assertIn(-176.0, [m['amount'] for m in fx_data['moves']])
        self.assertEqual(data['default_cash_details']['amount'], 100.0)
        summary = data['nm_exchange_summary']
        self.assertEqual(summary['count'], 1)
        self.assertEqual(summary['commission'], 3.2)
        self.assertEqual(summary['rate_margin'], 8.8)
        self.assertEqual(summary['operations'][0]['name'], exchange.name)
        self.assertEqual(session.nm_exchange_count, 1)
        self.assertEqual(session.nm_exchange_commission, 3.2)
        self.assertEqual(self.pos_config.nm_exchange_count, 1)

        # Closing at the expected amounts: no difference anywhere.
        self._close(session, main=100.0, fx=324.0)
        self.assertEqual(detail.difference_amount, 0.0)
        self.assertEqual(session.state, 'closed')
        # Report block.
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=session.ids)
        self.assertEqual(report['nm_exchange']['count'], 1)
        self.assertEqual(report['nm_exchange']['totals'][0]['commission'], 3.2)
        self.assertEqual(report['nm_exchange']['totals'][0]['rate_margin'], 8.8)
        values = self.env['report.point_of_sale.report_saledetails']._get_report_values(session.ids)
        self.assertIn('nm_exchange', values)
        # Position report sees the drawer at 324.
        self.env.flush_all()
        position = self.env['pos.nm.currency.position'].search([
            ('journal_id', '=', self.cash_journal.id), ('currency_id', '=', self.fx.id)])
        self.assertEqual(position.balance, 324.0)

    def test_exchange_foreign_to_main(self):
        """The main drawer is checked like the foreign ones: 50 cannot hand
        back 97, 150 can."""
        session = self._open(fx=0.0, main=50.0)
        Exchange = self.env['pos.nm.exchange']
        with self.assertRaisesRegex(UserError, 'cannot be handed back'):
            Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)
        session.try_cash_in_out('in', 100.0, 'float', self.partner_id)
        receipt = Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)
        exchange = self.env['pos.nm.exchange'].browse(receipt['id'])
        self.assertEqual(exchange.amount_out, 97.0)
        self.assertEqual(exchange.commission, 3.0)
        self.assertEqual(exchange.statement_line_in_id.amount_currency, 220.0)
        self.assertEqual(exchange.statement_line_in_id.amount, 100.0)
        self.assertEqual(exchange.statement_line_out_id.amount, -97.0)
        self.assertFalse(exchange.statement_line_out_id.foreign_currency_id)
        self.assertEqual(self.pos_config._nm_currency_balance(self.fx), 220.0)
        self._close(session, main=53.0, fx=220.0)

    def test_exchange_checks(self):
        session = self._open(fx=100.0)
        Exchange = self.env['pos.nm.exchange']
        # Not enough notes in the drawer.
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        # Customer required above the threshold.
        self.pos_config.nm_exchange_customer_threshold = 30.0
        identification = Exchange._nm_identification(self.pos_config, 40.0, self.env['res.partner'])
        self.assertTrue(identification['customer_required'])
        self.assertFalse(identification['document_required'])
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 40.0, self.fx.id)
        receipt = Exchange.create_from_ui(session.id, self.main.id, 40.0, self.fx.id, self.partner_id)
        exchange = Exchange.browse(receipt['id'])
        self.assertEqual(exchange.partner_id.id, self.partner_id)
        # 2% of 40 + 1 = 1.80, below the minimum: 3. 37 x 2 / 1.1 = 67.27,
        # rounded down to 67 EUR worth 36.85: commission 3.15.
        self.assertEqual(exchange.amount_out, 67.0)
        self.assertEqual(exchange.commission, 3.15)
        self.assertIn(self.env.user.partner_id.name, receipt['partner_name'])
        self.pos_config.nm_exchange_customer_threshold = 0.0
        # No commission account.
        self.pos_config.nm_exchange_income_account_id = False
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 10.0, self.fx.id)
        self.pos_config.nm_exchange_income_account_id = self.commission_account
        # Counter disabled.
        self.pos_config.nm_exchange_enabled = False
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 10.0, self.fx.id)
        self.pos_config.nm_exchange_enabled = True
        # Too small to hand back a single note.
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 0.2, self.fx.id)
        # Closed session.
        self._refresh_journal()
        balance = self.pos_config._nm_currency_balance(self.fx)
        self._close(session, main=40.0, fx=balance)
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 10.0, self.fx.id)

    # ------------------------------------------------------------------
    # Access rights and integrity
    # ------------------------------------------------------------------

    def test_access_rights(self):
        """A cashier records operations through the register only: the
        server decides the cashier, and the statement lines carry the
        cashier, not the customer."""
        session = self._open(fx=500.0)
        customer = self.env['res.partner'].create({'name': 'NM Customer'})
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 100.0, self.fx.id)
        self.assertEqual(quote['amount_out'], 176.0)
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id)
        exchange = Exchange.browse(receipt['id'])
        self.assertEqual(exchange.user_id, self.pos_user)
        self.assertEqual(exchange.cashier_name, 'NM Cashier')
        self.assertEqual(exchange.partner_id, customer)
        lines = exchange.sudo().statement_line_in_id | exchange.sudo().statement_line_out_id
        self.assertEqual(lines.partner_id, self.pos_user.partner_id)
        self.assertEqual(lines.create_uid, self.pos_user)
        # The foreign leg shows the cashier in the closing control.
        data = session.get_closing_control_data()
        fx_data = next(d for d in data['multicurrency_details'] if d['currency_id'] == self.fx.id)
        self.assertIn('NM Cashier', [m['cashier_name'] for m in fx_data['moves']])
        # Read only through the ORM.
        with self.assertRaises(AccessError):
            Exchange.create({
                'session_id': session.id, 'currency_in_id': self.main.id, 'currency_out_id': self.fx.id,
                'amount_in': 1.0, 'commission': 5000.0})
        with self.assertRaises(AccessError):
            exchange.write({'note': 'edited'})
        with self.assertRaises(AccessError):
            exchange.unlink()
        with self.assertRaises(AccessError):
            exchange.action_cancel()
        # The manager may edit the note only, and delete nothing.
        exchange = exchange.with_user(self.env.user)
        exchange.note = 'checked'
        self.assertEqual(exchange.note, 'checked')
        with self.assertRaises(UserError):
            exchange.write({'commission': 0.0})
        with self.assertRaises(UserError):
            exchange.unlink()
        # A user without the Point of Sale cannot use the counter.
        stranger = new_test_user(self.env, login='nm_exchange_stranger', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['pos.nm.exchange'].with_user(stranger).get_quote(
                self.pos_config.id, self.main.id, 100.0, self.fx.id)
        with self.assertRaises(AccessError):
            self.env['pos.nm.exchange'].with_user(stranger).create_from_ui(
                session.id, self.main.id, 100.0, self.fx.id)

    def test_multi_company(self):
        session = self._open(fx=500.0)
        receipt = self.env['pos.nm.exchange'].create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        exchange = self.env['pos.nm.exchange'].browse(receipt['id'])
        self.assertEqual(exchange.company_id, self.company)
        other_company = self.env['res.company'].create({'name': 'NM Other Company'})
        other_manager = new_test_user(
            self.env, login='nm_exchange_other_manager', groups='point_of_sale.group_pos_manager',
            company_id=other_company.id, company_ids=[(6, 0, other_company.ids)])
        Exchange = self.env['pos.nm.exchange'].with_user(other_manager)
        self.assertFalse(Exchange.search([('id', '=', exchange.id)]))
        with self.assertRaises(AccessError):
            exchange.with_user(other_manager).read(['name', 'partner_id', 'commission'])
        # The commission account belongs to the company of the point of sale.
        other_account = self.env['account.account'].create({
            'name': 'NM Other Commissions', 'code': '999055', 'account_type': 'income_other',
            'company_ids': [(6, 0, other_company.ids)]})
        with self.assertRaises(UserError):
            self.pos_config.nm_exchange_income_account_id = other_account
        # And it is an income account.
        with self.assertRaises(ValidationError):
            self.pos_config.nm_exchange_income_account_id = self.loss_account

    def test_exchange_leg_not_deletable(self):
        session = self._open(fx=500.0)
        receipt = self.env['pos.nm.exchange'].create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        exchange = self.env['pos.nm.exchange'].browse(receipt['id'])
        for line in (exchange.statement_line_in_id, exchange.statement_line_out_id):
            with self.assertRaises(UserError):
                session.delete_cash_in_out(line.id, self.partner_id)
            with self.assertRaises(UserError):
                line.unlink()
        self.assertTrue(exchange.statement_line_in_id.exists() and exchange.statement_line_out_id.exists())
        detail = session.currency_detail_ids.filtered(lambda d: d.currency_id == self.fx)
        self.assertEqual(detail.cash_moves_amount, -176.0)
        # Other cash moves still can be deleted.
        session.try_cash_in_out('in', 10.0, 'float', self.partner_id)
        move = session.sudo().bank_statement_line_ids.sorted('id')[-1]
        session.delete_cash_in_out(move.id, self.partner_id)
        self.assertFalse(move.exists())

    def _commission_balance(self):
        self.env.flush_all()
        lines = self.env['account.move.line'].search([('account_id', '=', self.commission_account.id)])
        return self.main.round(sum(lines.mapped('balance')))

    def test_cancel_exchange(self):
        """A manager cancels an operation while its session is open: two
        opposite lines bring the drawers and the commission account back to
        their state before the operation."""
        session = self._open(fx=500.0, main=100.0)
        Exchange = self.env['pos.nm.exchange']
        commission_before = self._commission_balance()
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        exchange = Exchange.browse(receipt['id'])
        kept = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)['id'])
        self.assertAlmostEqual(self._commission_balance(), commission_before - 3.2 - 3.0, places=2)
        # Not by a cashier.
        with self.assertRaises(AccessError):
            exchange.with_user(self.pos_user).action_cancel()

        exchange.action_cancel()
        self.assertEqual(exchange.state, 'cancelled')
        self.assertEqual(exchange.cancel_user_id, self.env.user)
        self.assertTrue(exchange.cancel_date)
        for line, reversal in ((exchange.statement_line_in_id, exchange.statement_line_cancel_in_id),
                               (exchange.statement_line_out_id, exchange.statement_line_cancel_out_id)):
            self.assertEqual(reversal.amount, -line.amount)
            self.assertEqual(reversal.amount_currency, -line.amount_currency)
            self.assertEqual(reversal.foreign_currency_id, line.foreign_currency_id)
            self.assertEqual(reversal.pos_session_id, session)
            self.assertIn(self.commission_account, reversal.move_id.line_ids.account_id)
        self.assertAlmostEqual(self._commission_balance(), commission_before - 3.0, places=2)
        # Drawers: only the operation kept is left (220 EUR in, 97 out of the
        # 100 counted at opening).
        self.assertEqual(self.pos_config._nm_currency_balance(self.fx), 720.0)
        detail = session.currency_detail_ids.filtered(lambda d: d.currency_id == self.fx)
        self.assertEqual(detail.cash_moves_amount, 220.0)
        self._refresh_journal()
        data = session.get_closing_control_data()
        self.assertEqual(data['default_cash_details']['amount'], 3.0)
        summary = data['nm_exchange_summary']
        self.assertEqual(summary['count'], 1)
        self.assertEqual(summary['cancelled_count'], 1)
        self.assertEqual(summary['commission'], 3.0)
        self.assertEqual([op['name'] for op in summary['operations']], [kept.name])
        self.assertEqual(session.nm_exchange_count, 1)
        self.assertEqual(session.nm_exchange_commission, 3.0)
        self.assertEqual(self.pos_config.nm_exchange_count, 1)
        # The buttons open the operations done, as they count them.
        for action in (session.action_nm_view_exchanges(), self.pos_config.action_nm_view_exchanges()):
            self.assertEqual(action['context'].get('search_default_done'), 1)
        # Once only, and the reversal lines are protected too.
        with self.assertRaises(UserError):
            exchange.action_cancel()
        with self.assertRaises(UserError):
            exchange.statement_line_cancel_out_id.unlink()

        self._close(session, main=3.0, fx=720.0)
        self.assertEqual(detail.difference_amount, 0.0)
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=session.ids)
        self.assertEqual(report['nm_exchange']['count'], 1)
        self.assertEqual(report['nm_exchange']['cancelled_count'], 1)
        self.assertIn(exchange.name, report['nm_exchange']['cancelled_label'])
        self.assertEqual([op['name'] for op in report['nm_exchange']['operations']], [kept.name])
        self.assertEqual(len(report['nm_exchange']['totals']), 1)
        self.assertEqual(report['nm_exchange']['totals'][0]['count'], 1)
        self.assertEqual(report['nm_exchange']['totals'][0]['commission'], 3.0)
        # Not once the session is closed.
        with self.assertRaisesRegex(UserError, 'closed session'):
            kept.action_cancel()
        self.assertEqual(kept.state, 'done')

    def test_cancel_needs_the_notes(self):
        """The notes received must still be in the drawer to be handed back."""
        session = self._open(fx=0.0, main=100.0)
        Exchange = self.env['pos.nm.exchange']
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)['id'])
        session.nm_try_cash_in_out_currency('out', 200.0, 'bank deposit', self.partner_id, self.fx.id)
        with self.assertRaises(UserError):
            exchange.action_cancel()
        self.assertEqual(exchange.state, 'done')

    def test_gapless_reference(self):
        """An operation refused after its number was drawn gives the number
        back: the register of operations has no hole."""
        sequence = self.env.ref('pos_nm_currency_exchange.seq_pos_nm_exchange')
        self.assertEqual(sequence.implementation, 'no_gap')
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        first = Exchange.create_from_ui(session.id, self.main.id, 10.0, self.fx.id)['name']
        # Refused before the number: not enough notes in the drawer.
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 1000.0, self.fx.id)
        # Refused after the number, while posting the lines.
        with patch.object(self.registry['pos.nm.exchange'], '_nm_post_line', side_effect=UserError('refused')), \
                self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 10.0, self.fx.id)
        second = Exchange.create_from_ui(session.id, self.main.id, 10.0, self.fx.id)['name']
        self.assertEqual(int(second.rsplit('/', 1)[1]), int(first.rsplit('/', 1)[1]) + 1)
        self.assertEqual(Exchange.search_count([('session_id', '=', session.id)]), 2)

    def test_pos_hr_employee(self):
        """With the Employees module, the employee logged in at the register
        is the cashier of the operation and of its statement lines."""
        if 'hr.employee' not in self.env:
            self.skipTest("pos_hr is not installed")
        cashier = self.env['hr.employee'].sudo().create({'name': 'NM Employee', 'company_id': self.company.id})
        stranger = self.env['hr.employee'].sudo().create({'name': 'NM Stranger', 'company_id': self.company.id})
        self.pos_config.write({'module_pos_hr': True, 'cashier_employee_ids': [(6, 0, cashier.ids)]})
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, employee_id=stranger.id)
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, employee_id=cashier.id)
        exchange = Exchange.browse(receipt['id'])
        self.assertEqual(exchange.cashier_name, 'NM Employee')
        self.assertEqual(exchange.user_id, self.env.user)
        lines = exchange.statement_line_in_id | exchange.statement_line_out_id
        self.assertEqual(lines.employee_id, cashier)
        self.assertEqual(lines.partner_id, cashier.work_contact_id)
        moves = session.get_cash_in_out_list()
        self.assertIn('NM Employee', [m['cashier_name'] for m in moves if m['id'] == exchange.statement_line_in_id.id])

    # ------------------------------------------------------------------
    # Drawers, currencies and quotes
    # ------------------------------------------------------------------

    def test_drawer_check_with_session_sales(self):
        """The notes taken in the sales of the session can be handed back,
        and the main drawer is checked too, its sales included."""
        session = self._open(fx=0.0, main=0.0)
        Exchange = self.env['pos.nm.exchange']
        # 21.20 EUR paid in cash for a sale.
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6, 'foreign_currency_id': self.fx.id,
                                            'amount_currency': 21.2}]],
            products=[[self.product_6, {}]],
        )
        # 9 main: commission 3, 6 x 2 / 1.1 = 10.9 -> 10 EUR out of the 21.20.
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 9.0, self.fx.id)['id'])
        self.assertEqual(exchange.amount_out, 10.0)
        self.assertEqual(session._nm_expected_cash(self.fx), 11.2)
        # 13 main would take 18 EUR out of the 11.20 left.
        with self.assertRaisesRegex(UserError, 'cannot be handed back'):
            Exchange.create_from_ui(session.id, self.main.id, 13.0, self.fx.id)
        # Main drawer: 9 received plus 10.60 of a sale paid in cash.
        self.create_pos_order(payment_method=[[self.cash_pm, {'amount': 10.6}]], products=[[self.product_6, {}]])
        self.assertEqual(session._nm_expected_cash(self.main), 19.6)
        # 55 EUR worth 25, commission 3: 22 cannot be handed back from 19.60.
        with self.assertRaisesRegex(UserError, 'cannot be handed back'):
            Exchange.create_from_ui(session.id, self.fx.id, 55.0, self.main.id)
        # 44 EUR worth 20, commission 3: 17 can.
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 44.0, self.main.id)['id'])
        self.assertEqual(exchange.amount_out, 17.0)
        self.assertEqual(session._nm_expected_cash(self.main), 2.6)

    def test_foreign_to_foreign(self):
        """EUR -> CHF, each with its own setting. CHF: 0.8 for 1 main at the
        rate of Odoo, 5% sell margin, 1% commission, 5 CHF notes.

        220 EUR are worth 100 (cash rate 2.2). The commission is the one of
        the currency handed back: 1. 99 x 0.8 / 1.05 = 75.43 CHF, rounded down
        to 75, worth 75 x 1.05 / 0.8 = 98.4375 -> 98.44: commission 1.56.
        Rate margin: 220 EUR are worth 110 at the rate of Odoo and 75 CHF
        93.75, so 110 - 100 + 98.44 - 93.75 = 14.69."""
        chf = self._add_cash_currency(
            'CHF', 0.8, margin_percent=5.0, exchange_sell_margin_percent=5.0, change_rounding=5.0,
            exchange_commission_percent=1.0)
        quote = self._quote(self.fx, 220.0, chf)
        self.assertEqual(quote['value_in'], 100.0)
        self.assertEqual(quote['amount_out'], 75.0)
        self.assertEqual(quote['value_out'], 98.44)
        self.assertEqual(quote['commission'], 1.56)
        self.assertEqual(quote['rate_margin'], 14.69)
        # CHF -> EUR: the commission of EUR, at least 3. 80 CHF at the cash
        # rate 0.84 are worth 95.24; 92.24 x 2 / 1.1 = 167.7 -> 167 EUR, worth
        # 91.85: commission 3.39.
        quote = self._quote(chf, 80.0, self.fx)
        self.assertEqual(quote['value_in'], 95.24)
        self.assertEqual(quote['amount_out'], 167.0)
        self.assertEqual(quote['commission'], 3.39)

        session = self._open(fx=0.0, counts={chf: 100.0})
        Exchange = self.env['pos.nm.exchange']
        # 440 EUR would take 150 CHF out of 100.
        with self.assertRaisesRegex(UserError, 'cannot be handed back'):
            Exchange.create_from_ui(session.id, self.fx.id, 440.0, chf.id)
        commission_before = self._commission_balance()
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 220.0, chf.id)['id'])
        line_in, line_out = exchange.statement_line_in_id, exchange.statement_line_out_id
        self.assertEqual((line_in.foreign_currency_id, line_in.amount_currency, line_in.amount), (self.fx, 220.0, 100.0))
        self.assertEqual((line_out.foreign_currency_id, line_out.amount_currency, line_out.amount), (chf, -75.0, -98.44))
        details = {detail.currency_id: detail.cash_moves_amount for detail in session.currency_detail_ids}
        self.assertEqual(details[self.fx], 220.0)
        self.assertEqual(details[chf], -75.0)
        self.assertAlmostEqual(self._commission_balance(), commission_before - 1.56, places=2)
        self.assertEqual(session._nm_expected_cash(chf), 25.0)

        # Without a CHF setting: the commission of EUR, no rounding step and
        # no sell margin: 97 x 0.8 = 77.60 CHF.
        self.env['pos.nm.currency.setting'].search([('currency_id', '=', chf.id)]).unlink()
        quote = self._quote(self.fx, 220.0, chf)
        self.assertEqual(quote['commission'], 3.0)
        self.assertEqual(quote['amount_out'], 77.6)

    def test_zero_decimal_currency(self):
        """VND, no decimals, 25,000 for 1 main, 2% sell margin, 1,000 VND
        notes, 1% commission.

        100 main: 99 x 25,000 / 1.02 = 2,426,470.6 VND, rounded down to
        2,426,000, worth 98.98: commission 1.02; at the rate of Odoo they are
        worth 97.04, rate margin 1.94.
        2,500,000 VND are worth 100: 99 main handed back, a rate of 0.0000396
        main for 1 VND, stored as is."""
        vnd = self._add_cash_currency(
            'VND', 25000.0, exchange_sell_margin_percent=2.0, change_rounding=1000.0,
            exchange_commission_percent=1.0)
        quote = self._quote(self.main, 100.0, vnd)
        self.assertEqual(quote['amount_out'], 2426000.0)
        self.assertEqual(quote['value_out'], 98.98)
        self.assertEqual(quote['commission'], 1.02)
        self.assertEqual(quote['rate_margin'], 1.94)

        session = self._open(fx=0.0, main=200.0, counts={vnd: 0.0})
        Exchange = self.env['pos.nm.exchange']
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, vnd.id, 2500000.0, self.main.id)['id'])
        self.assertEqual(exchange.value_in, 100.0)
        self.assertEqual(exchange.amount_out, 99.0)
        self.assertAlmostEqual(exchange.rate, 0.0000396, places=12)
        self.assertIn('1 %s = ' % self.main.name, exchange.rate_label)
        self.assertIn('25,252.53', exchange.rate_label)

    def test_rate_margin_realized_at_revaluation(self):
        """The rate margin of the operations is what the revaluation of the
        drawer posts at closing: a gain, never a loss.

        500 EUR at opening, booked at the rate of Odoo: 250. 100 main buy 176
        EUR booked 96.80 (rate margin 8.80), 220 EUR are bought for 97 main,
        booked 100 (rate margin 10). The drawer holds 544 EUR worth 272,
        booked 250 - 96.80 + 100 = 253.20: revaluation +18.80."""
        gain = self.env['account.account'].create({
            'name': 'EX Exchange Gain', 'code': '999054', 'account_type': 'income_other'})
        loss = self.env['account.account'].create({
            'name': 'EX Exchange Loss', 'code': '999055', 'account_type': 'expense'})
        self.company.write({
            'income_currency_exchange_account_id': gain.id, 'expense_currency_exchange_account_id': loss.id})
        self.pos_config.nm_revaluation_enabled = True
        session = self._open(fx=500.0, main=200.0)
        Exchange = self.env['pos.nm.exchange']
        exchanges = Exchange.browse([
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'],
            Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)['id'],
        ])
        self.assertEqual(exchanges.mapped('rate_margin'), [8.8, 10.0])
        self._close(session, main=203.0, fx=544.0)
        detail = session.currency_detail_ids.filtered(lambda d: d.currency_id == self.fx)
        self.assertEqual(detail.difference_amount, 0.0)
        self.assertEqual(detail.revaluation_amount, 18.8)
        self.assertIn(gain, detail.revaluation_line_id.move_id.line_ids.account_id)

    def test_quote_changed(self):
        """The register sends the amount it showed: refused when the quote
        changed in the meantime."""
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 100.0, self.fx.id)
        self.assertEqual(quote['amount_out'], 176.0)
        # The manager lowers the sell margin: 97 x 2 / 1.05 = 184.76 -> 184.
        self.setting.exchange_sell_margin_percent = 5.0
        with self.assertRaisesRegex(UserError, 'quote changed'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, amount_out=quote['amount_out'])
        self.assertFalse(Exchange.search([('session_id', '=', session.id)]))
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, amount_out=184.0)
        self.assertEqual(Exchange.browse(receipt['id']).amount_out, 184.0)

    def test_create_from_ui_uuid(self):
        """Confirmed again with the same identifier (the response of the first
        call was lost): the operation is recorded once and its receipt is
        returned again."""
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, uuid='nm-uuid-1')
        lines = session.bank_statement_line_ids
        # Even when the cashier changed the amount before confirming again.
        again = Exchange.create_from_ui(session.id, self.main.id, 50.0, self.fx.id, uuid='nm-uuid-1')
        self.assertEqual(again, receipt)
        self.assertEqual(len(session.nm_exchange_ids), 1)
        self.assertEqual(session.nm_exchange_ids.uuid, 'nm-uuid-1')
        self.assertEqual(session.bank_statement_line_ids, lines)
        self.assertEqual(session._nm_expected_cash(self.fx), 324.0)
        # Another identifier is another operation.
        Exchange.create_from_ui(session.id, self.main.id, 50.0, self.fx.id, uuid='nm-uuid-2')
        self.assertEqual(len(session.nm_exchange_ids), 2)
        # The identifier is unique.
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.cr.savepoint():
            self.env['pos.nm.exchange'].sudo().create({
                'session_id': session.id, 'currency_in_id': self.main.id, 'currency_out_id': self.fx.id,
                'uuid': 'nm-uuid-1'})

    def test_register_data(self):
        """The register knows whether the commission account is set: it
        explains why the counter cannot be used instead of opening it."""
        def account_set():
            return self.pos_config._load_pos_data_read(self.pos_config, self.pos_config)[0]['_nm_exchange_account_set']
        self.assertTrue(account_set())
        self.pos_config.nm_exchange_income_account_id = False
        self.assertFalse(account_set())

    def test_get_quote_drawer(self):
        """The quote shows the drawer of the currency handed back, and the
        refusal of the drawer check before the operation is confirmed."""
        Exchange = self.env['pos.nm.exchange']
        # No open session: no drawer.
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 100.0, self.fx.id)
        self.assertEqual((quote['drawer_balance_formatted'], quote['drawer_error']), ('', ''))
        self._open(fx=100.0)
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 50.0, self.fx.id)
        self.assertEqual(quote['drawer_balance_formatted'], self.fx.format(100.0))
        self.assertFalse(quote['drawer_error'])
        # 176 EUR cannot be handed back from 100.
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 100.0, self.fx.id)
        self.assertIn('cannot be handed back', quote['drawer_error'])

    def _assert_reverse(self, currency_in, currency_out, amount_out, amount_in):
        """The reverse quote of ``amount_out`` is ``amount_in``: its quote hands
        back at least ``amount_out``, one payment step less does not."""
        Exchange = self.env['pos.nm.exchange']
        result = Exchange._nm_reverse_amount_in(self.pos_config, currency_in, currency_out, amount_out)
        self.assertEqual(result, amount_in)
        step = Exchange._nm_payment_step(self.pos_config, currency_in)
        self.assertGreaterEqual(self._quote(currency_in, result, currency_out)['amount_out'], amount_out)
        self.assertLess(self._quote(currency_in, result - step, currency_out)['amount_out'], amount_out)

    def test_reverse_quote(self):
        """The customer asks for an amount: the smallest amount received,
        rounded up to the coins and notes of its currency, whose quote hands
        back at least that much."""
        # 176 EUR are worth 96.80 at the sell rate: 99.80 with the minimum
        # commission of 3.
        self._assert_reverse(self.main, self.fx, 176.0, 99.8)
        # 175.50 EUR cannot be handed back with 1 EUR notes: 176.
        self._assert_reverse(self.main, self.fx, 175.5, 99.8)
        # Small amount: the minimum commission. 10 EUR are worth 5.50.
        self._assert_reverse(self.main, self.fx, 10.0, 8.5)
        # Above 100 the commission is 2% + 1: 177 EUR are worth 97.35, so
        # 100.36 are needed.
        self._assert_reverse(self.main, self.fx, 177.0, 100.36)
        # The POS currency received is rounded up to its cash rounding.
        rounding = self.env['account.cash.rounding'].create({
            'name': 'NM 0.05', 'rounding': 0.05, 'rounding_method': 'HALF-UP',
            'profit_account_id': self.profit_account.id, 'loss_account_id': self.loss_account.id})
        self.pos_config.write({'cash_rounding': True, 'rounding_method': rounding.id})
        self._assert_reverse(self.main, self.fx, 177.0, 100.4)
        # Without payment rounding, a foreign currency received is rounded up
        # to its change rounding (1 EUR coins), as the register warns: 96
        # main need notes worth 99, 217.80 EUR, so 218.
        self._assert_reverse(self.fx, self.main, 96.0, 218.0)
        # The remainder of the change handed back in the POS currency: the
        # change rounding is no coin the customer must bring.
        self.setting.change_rest_mode = 'main'
        self._assert_reverse(self.fx, self.main, 96.0, 217.79)
        # A foreign currency received is rounded up to its payment rounding:
        # 97 main need notes worth 100, 220 EUR at the cash rate 2.2.
        self.setting.payment_rounding = 5.0
        self._assert_reverse(self.fx, self.main, 97.0, 220.0)
        self._assert_reverse(self.fx, self.main, 96.0, 220.0)

    def test_reverse_quote_zero_decimals(self):
        """VND without decimals, 25,000 for 1 main, 1% commission, 1,000 VND
        notes taken and handed back."""
        vnd = self._add_cash_currency(
            'VND', 25000.0, exchange_sell_margin_percent=2.0, change_rounding=1000.0, payment_rounding=1000.0,
            exchange_commission_percent=1.0)
        # 99 main: notes worth 100, 2,500,000 VND.
        self._assert_reverse(vnd, self.main, 99.0, 2500000.0)
        # 1,000,000 VND are worth 40.80 at the sell rate: 41.21 main less 1%.
        self._assert_reverse(self.main, vnd, 1000000.0, 41.21)

    def test_get_reverse_quote_rpc(self):
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        self._open(fx=500.0)
        quote = Exchange.get_reverse_quote(self.pos_config.id, self.main.id, self.fx.id, 175.5)
        # The quote of the amount received, recorded as any other.
        self.assertEqual(quote['amount_in'], 99.8)
        self.assertEqual(quote['amount_out'], 176.0)
        self.assertEqual(quote['commission'], 3.0)
        self.assertEqual(quote['drawer_balance_formatted'], self.fx.format(500.0))
        with self.assertRaisesRegex(UserError, 'must be positive'):
            Exchange.get_reverse_quote(self.pos_config.id, self.main.id, self.fx.id, 0.0)
        with self.assertRaises(UserError):
            Exchange.get_reverse_quote(self.pos_config.id, self.main.id, self.main.id, 100.0)
        # No rate to sell the notes at: nothing is ever handed back.
        with patch.object(type(self.pos_config), '_nm_exchange_sell_rate', lambda config, currency: 0.0), \
                self.assertRaisesRegex(UserError, 'No amount received'):
            Exchange.get_reverse_quote(self.pos_config.id, self.main.id, self.fx.id, 100.0)
        stranger = new_test_user(self.env, login='nm_reverse_stranger', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['pos.nm.exchange'].with_user(stranger).get_reverse_quote(
                self.pos_config.id, self.main.id, self.fx.id, 100.0)

    # ------------------------------------------------------------------
    # Sales Details report and closing
    # ------------------------------------------------------------------

    def _sale_details(self, hours_before=1, hours_after=1, **kwargs):
        """Sales Details by period around now, as the wizard calls it."""
        now = fields.Datetime.now()
        return self.env['report.point_of_sale.report_saledetails'].get_sale_details(
            fields.Datetime.to_string(now - timedelta(hours=hours_before)),
            fields.Datetime.to_string(now + timedelta(hours=hours_after)), **kwargs)

    def test_report_by_period(self):
        """Without sessions, the report takes the operations of the period on
        its points of sale: those of an open session without any order, not
        those of the same session made before the period."""
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        earlier = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        earlier.sudo().date = fields.Datetime.now() - timedelta(days=1)
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)['id'])

        report = self._sale_details(config_ids=self.pos_config.ids)
        block = report['nm_exchange']
        self.assertEqual([op['name'] for op in block['operations']], [exchange.name])
        self.assertEqual(block['totals'][0]['commission'], 3.0)
        self.assertEqual(block['totals'][0]['rate_margin'], 10.0)
        # Without points of sale: every point of sale.
        self.assertEqual(self._sale_details()['nm_exchange']['count'], 1)
        # The day before: the earlier operation only.
        report = self._sale_details(hours_before=25, hours_after=-23, config_ids=self.pos_config.ids)
        self.assertEqual([op['name'] for op in report['nm_exchange']['operations']], [earlier.name])
        # A period without operation, or another point of sale: no block.
        self.assertNotIn('nm_exchange', self._sale_details(hours_before=-1, hours_after=2))
        other_config = self.pos_config.copy({'name': 'NM Other Shop'})
        self.assertNotIn('nm_exchange', self._sale_details(config_ids=other_config.ids))
        # Printed from the session: all the operations of the session.
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=session.ids)
        self.assertEqual(report['nm_exchange']['count'], 2)

        # Once the session is closed, with exchanges only.
        self._close(session, main=3.0, fx=544.0)
        self.assertEqual(self._sale_details(config_ids=self.pos_config.ids)['nm_exchange']['count'], 1)

    def test_report_currencies(self):
        """Commissions of points of sale in different currencies are totalled
        per currency, never added together."""
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        xpf = self.setup_other_currency('XPF', rates=[('1900-01-01', 119.0)])
        journal = self.env['account.journal'].create({
            'name': 'NM XPF Sales', 'code': 'NMXPF', 'type': 'general', 'currency_id': xpf.id})
        xpf_config = self.env['pos.config'].create({
            'name': 'NM XPF Shop', 'journal_id': journal.id, 'payment_method_ids': [(6, 0, [])]})
        xpf_session = self.env['pos.session'].create({'config_id': xpf_config.id, 'user_id': self.env.uid})
        self.assertEqual(xpf_session.currency_id, xpf)
        Exchange.sudo().create({
            'session_id': xpf_session.id, 'currency_in_id': self.fx.id, 'currency_out_id': xpf.id,
            'amount_in': 100.0, 'amount_out': 11400.0, 'value_in': 12000.0, 'value_out': 11400.0,
            'commission': 600.0, 'rate_margin': 100.0})

        block = self._sale_details(config_ids=(self.pos_config | xpf_config).ids)['nm_exchange']
        self.assertEqual(block['count'], 2)
        totals = {total['currency']: total for total in block['totals']}
        self.assertEqual(set(totals), {self.main.name, xpf.name})
        self.assertEqual(totals[self.main.name]['commission'], 3.2)
        self.assertEqual(totals[xpf.name]['commission'], 600.0)
        self.assertEqual(totals[xpf.name]['rate_margin'], 100.0)
        self.assertIn(xpf.name, totals[xpf.name]['count_label'])
        # One point of sale: its own currency only.
        block = self._sale_details(config_ids=xpf_config.ids)['nm_exchange']
        self.assertEqual([total['currency'] for total in block['totals']], [xpf.name])

    def test_report_rendering(self):
        """The block is printed in the Sales Details of the session."""
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        cancelled = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 50.0, self.fx.id)['id'])
        cancelled.action_cancel()
        html, _format = self.env['ir.actions.report']._render_qweb_html(
            'point_of_sale.sale_details_report', session.ids)
        html = html.decode()
        self.assertIn('id="nm_exchange"', html)
        self.assertIn(exchange.name, html)
        self.assertIn(self.main.format(3.2), html)
        self.assertIn(self.main.format(8.8), html)
        self.assertIn('Rate Margin', html)
        self.assertIn('1 operations', html)
        self.assertIn('cancelled operations: %s' % cancelled.name, html)

    def test_closing_after_counter_disabled(self):
        """The closing popup lists the operations even when the counter was
        disabled during the session."""
        session = self._open(fx=500.0)
        self.env['pos.nm.exchange'].create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        self.pos_config.nm_exchange_enabled = False
        summary = session.get_closing_control_data()['nm_exchange_summary']
        self.assertEqual(summary['count'], 1)
        self.assertEqual(summary['commission'], 3.2)
        self.assertEqual(summary['rate_margin'], 8.8)
        # Nothing to show for a session without operation.
        self._close(session, main=100.0, fx=324.0)
        self.assertNotIn('nm_exchange_summary', self._open(fx=324.0).get_closing_control_data())

    # ------------------------------------------------------------------
    # Identification of the customer
    # ------------------------------------------------------------------

    def _document(self, **values):
        return {'type': 'passport', 'number': 'AB1234567', 'country_id': self.env.ref('base.fr').id,
                'expiry': str(fields.Date.today() + timedelta(days=365)), 'nationality_id': self.env.ref('base.fr').id,
                'birthdate': '1980-05-17', **values}

    def test_linked_operations(self):
        """Identity document above 1000 with the operations of the customer
        over 7 days: two operations of 900 reach 1800, the second one needs
        the document; another customer, or an operation older than the
        period, does not count."""
        self.pos_config.write({'nm_exchange_document_threshold': 1000.0, 'nm_exchange_linked_days': 7})
        session = self._open(fx=10000.0)
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        customer = self.env['res.partner'].create({'name': 'NM Linked Customer'})
        other = self.env['res.partner'].create({'name': 'NM Other Customer'})
        first = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 900.0, self.fx.id, customer.id)['id'])
        self.assertEqual(first.linked_value, 900.0)
        self.assertFalse(first.sudo().id_document_type)

        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 900.0, self.fx.id, customer.id)
        self.assertTrue(quote['document_required'])
        self.assertTrue(quote['customer_required'])
        self.assertEqual(quote['linked_value'], 1800.0)
        self.assertFalse(Exchange.get_quote(self.pos_config.id, self.main.id, 900.0, self.fx.id, other.id)[
            'document_required'])
        # Without customer: the operation alone, 900, needs nothing.
        self.assertFalse(Exchange.get_quote(self.pos_config.id, self.main.id, 900.0, self.fx.id)['document_required'])
        with self.assertRaisesRegex(UserError, r'last 7 days.*1,800\.00'):
            Exchange.create_from_ui(session.id, self.main.id, 900.0, self.fx.id, customer.id)
        # Above the threshold alone: a customer is required.
        with self.assertRaisesRegex(UserError, 'A customer with an identity document'):
            Exchange.create_from_ui(session.id, self.main.id, 1100.0, self.fx.id)

        # Outside the period, the first operation no longer counts.
        first.sudo().write({'date': fields.Datetime.now() - timedelta(days=8)})
        receipt = Exchange.create_from_ui(session.id, self.main.id, 900.0, self.fx.id, customer.id)
        self.assertEqual(Exchange.browse(receipt['id']).linked_value, 900.0)
        self.assertFalse(receipt['id_document'])
        # A cancelled operation does not count either.
        Exchange.browse(receipt['id']).with_user(self.env.user).action_cancel()
        self.assertEqual(Exchange._nm_linked_value(self.pos_config, 900.0, customer), 900.0)

    def test_identity_document(self):
        """The document typed at the register is checked, saved on the
        customer and frozen on the operation; the receipt shows its type and
        the end of its number only."""
        self.pos_config.write({'nm_exchange_document_threshold': 50.0})
        session = self._open(fx=10000.0)
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        customer = self.env['res.partner'].create({'name': 'NM Document Customer'})
        with self.assertRaisesRegex(UserError, 'identity document of the customer is required'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id)
        expired = self._document(expiry=str(fields.Date.today() - timedelta(days=1)))
        with self.assertRaisesRegex(UserError, 'expired'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id, document=expired)
        with self.assertRaisesRegex(UserError, 'expiry date'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id,
                                    document=self._document(expiry=''))
        # Nothing saved from the refused documents.
        self.assertFalse(customer.nm_id_document_number)

        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id,
                                          document=self._document())
        self.assertEqual(receipt['id_document'], 'Passport ****4567')
        self.assertNotIn('AB1234567', str(receipt))
        exchange = Exchange.browse(receipt['id']).with_user(self.env.user)
        self.assertEqual(customer.nm_id_document_number, 'AB1234567')
        self.assertEqual(customer.nm_birthdate, fields.Date.to_date('1980-05-17'))
        self.assertEqual(exchange.id_document_type, 'passport')
        self.assertEqual(exchange.id_document_number, 'AB1234567')
        self.assertEqual(exchange.id_document_country_id, self.env.ref('base.fr'))
        self.assertEqual(exchange.id_nationality_id, self.env.ref('base.fr'))
        self.assertEqual(exchange.customer_name, 'NM Document Customer')

        # The register prefills the document of the customer.
        loaded = Exchange.get_customer_document(customer.id)
        self.assertEqual(loaded['document']['number'], 'AB1234567')
        self.assertEqual(loaded['document']['birthdate'], '1980-05-17')
        self.assertIn('passport', dict(loaded['types']))
        # Without a document sent, the one of the customer is used.
        second = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id)
        self.assertEqual(second['id_document'], 'Passport ****4567')

        # Later changes of the customer do not change the operation.
        customer.write({'name': 'NM Renamed', 'nm_id_document_number': 'ZZ0000000',
                        'nm_id_document_type': 'id_card'})
        exchange.invalidate_recordset()
        self.assertEqual(exchange.id_document_number, 'AB1234567')
        self.assertEqual(exchange.id_document_type, 'passport')
        self.assertEqual(exchange.customer_name, 'NM Document Customer')
        self.assertEqual(exchange._nm_receipt_data()['partner_name'], 'NM Document Customer')
        # An expired document of the customer is refused too.
        customer.nm_id_document_expiry = fields.Date.today() - timedelta(days=1)
        with self.assertRaisesRegex(UserError, 'expired'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id)

    def test_customer_always(self):
        self.pos_config.nm_exchange_customer_always = True
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        self.assertTrue(Exchange.get_quote(self.pos_config.id, self.main.id, 10.0, self.fx.id)['customer_required'])
        with self.assertRaisesRegex(UserError, 'every exchange operation'):
            Exchange.create_from_ui(session.id, self.main.id, 10.0, self.fx.id)
        receipt = Exchange.create_from_ui(session.id, self.main.id, 10.0, self.fx.id, self.partner_id)
        self.assertEqual(Exchange.browse(receipt['id']).partner_id.id, self.partner_id)
        with self.assertRaises(ValidationError):
            self.pos_config.nm_exchange_linked_days = -1
        with self.assertRaises(ValidationError):
            self.pos_config.nm_exchange_document_threshold = -1

    def test_identity_fields_access(self):
        """The POS users do not read the identity documents of the contacts
        or of the operations, except through the register."""
        customer = self.env['res.partner'].create({
            'name': 'NM Private Customer', 'nm_id_document_type': 'passport', 'nm_id_document_number': 'SECRET99'})
        Partner = self.env['res.partner'].with_user(self.pos_user)
        with self.assertRaises(AccessError):
            Partner.search_read([('id', '=', customer.id)], ['name', 'nm_id_document_number'])
        record = Partner.search_read([('id', '=', customer.id)])[0]
        self.assertNotIn('nm_id_document_number', record)
        self.assertNotIn('SECRET99', str(record))
        with self.assertRaises(AccessError):
            Partner.browse(customer.id).write({'nm_id_document_number': 'FORGED'})
        with self.assertRaises(AccessError):
            self.env['pos.nm.exchange'].with_user(self.pos_user).search_read([], ['id_document_number'])
        self.assertEqual(self.env['pos.nm.exchange'].with_user(self.pos_user).get_customer_document(
            customer.id)['document']['number'], 'SECRET99')
