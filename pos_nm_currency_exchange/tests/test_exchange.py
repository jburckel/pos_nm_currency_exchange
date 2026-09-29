# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_pos_accounting import TestPosAccounting


@tagged('post_install', '-at_install')
class TestPosCurrencyExchange(TestPosAccounting):
    """Exchange counter on the drawers of pos_nm_multicurrencies.

    ``setup_other_currency``: 1 company currency = 2 foreign units at the
    latest rate; a 10% margin makes the cash rate 2.2.
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
            'change_rounding': 1.0,
            'exchange_commission_percent': 2.0,
            'exchange_commission_fixed': 1.0,
            'exchange_commission_min': 3.0,
        })
        cls.partner_id = cls.env.user.partner_id.id

    def _refresh_journal(self):
        self.cash_journal.invalidate_recordset(['current_statement_balance', 'has_statement_lines'])

    def _open(self, fx=0.0):
        self._refresh_journal()
        self.pos_config.open_ui()
        session = self.get_pos_session()
        session.set_multicurrency_counts({str(self.fx.id): fx})
        session.set_opening_control(0.0, '')
        session.bank_statement_id.flush_recordset()
        return session

    def _close(self, session, main=0.0, fx=0.0):
        self._refresh_journal()
        session.set_multicurrency_counts({self.fx.id: fx})
        result = session.close_session_from_ui({self.cash_pm.id: main})
        self.assertTrue(result['status'], result)

    def _quote(self, currency_in, amount_in, currency_out):
        return self.env['pos.nm.exchange']._nm_quote(self.pos_config, currency_in, amount_in, currency_out)

    # ------------------------------------------------------------------

    def test_setting_constraints(self):
        with self.assertRaises(ValidationError):
            self.setting.exchange_commission_percent = -1
        with self.assertRaises(ValidationError):
            self.setting.exchange_commission_percent = 100
        with self.assertRaises(ValidationError):
            self.pos_config.nm_exchange_customer_threshold = -1
        self.assertEqual(self.setting._nm_exchange_commission(100.0), 3.0)   # 2 + 1, at least 3
        self.assertEqual(self.setting._nm_exchange_commission(1000.0), 21.0)  # 20 + 1
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
        """100 main received: commission 3, 97 to hand back = 213.4 EUR at
        the change rate 2.2, rounded down to the 1 EUR note: 213 EUR worth
        96.82, commission 3.18."""
        quote = self._quote(self.main, 100.0, self.fx)
        self.assertEqual(quote['value_in'], 100.0)
        self.assertEqual(quote['amount_out'], 213.0)
        self.assertEqual(quote['value_out'], 96.82)
        self.assertEqual(quote['commission'], 3.18)
        self.assertAlmostEqual(quote['rate'], 2.13, places=6)
        self.assertFalse(quote['customer_required'])

    def test_quote_foreign_to_main(self):
        """220 EUR received at the cash rate 2.2: worth 100, commission 3,
        97 handed back in the main currency."""
        quote = self._quote(self.fx, 220.0, self.main)
        self.assertEqual(quote['value_in'], 100.0)
        self.assertEqual(quote['commission'], 3.0)
        self.assertEqual(quote['amount_out'], 97.0)
        self.assertEqual(quote['value_out'], 97.0)
        self.assertAlmostEqual(quote['rate'], 97.0 / 220.0, places=6)

    def test_quote_fixed_change_rate(self):
        self.setting.write({'rate_mode': 'fixed', 'fixed_rate': 2.5, 'fixed_change_rate': 2.4})
        # Received at the fixed rate, handed back at the fixed change rate.
        quote = self._quote(self.fx, 250.0, self.main)
        self.assertEqual(quote['value_in'], 100.0)
        quote = self._quote(self.main, 100.0, self.fx)
        self.assertEqual(quote['amount_out'], 232.0)  # 97 x 2.4 = 232.8 -> 232
        self.assertEqual(quote['value_out'], 96.67)
        self.setting.write({'rate_mode': 'odoo', 'fixed_rate': 0.0, 'fixed_change_rate': 0.0})

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
        self.assertEqual(quote['amount_out'], 213.0)
        self.assertIn('213', quote['amount_out_formatted'])
        self.assertIn('rate_label', quote)
        with self.assertRaises(UserError):
            self.env['pos.nm.exchange'].get_quote(self.pos_config.id, self.main.id, 100.0, self.main.id)
        with self.assertRaises(UserError):
            self.env['pos.nm.exchange'].get_quote(self.pos_config.id, self.main.id, -5.0, self.fx.id)
        gbp = self.env.ref('base.GBP')
        gbp.active = True
        with self.assertRaises(UserError):
            self.env['pos.nm.exchange'].get_quote(self.pos_config.id, self.main.id, 100.0, gbp.id)

    def test_exchange_operation(self):
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, False, 'Marie', 'tourist')
        exchange = Exchange.browse(receipt['id'])
        self.assertTrue(exchange.name.startswith('EXC/'))
        self.assertEqual(exchange.session_id, session)
        self.assertEqual(exchange.config_id, self.pos_config)
        self.assertEqual(exchange.cashier_name, 'Marie')
        self.assertEqual(exchange.note, 'tourist')
        self.assertEqual(exchange.amount_in, 100.0)
        self.assertEqual(exchange.amount_out, 213.0)
        self.assertEqual(exchange.commission, 3.18)
        self.assertIn('213', receipt['amount_out'])
        self.assertIn('Marie', receipt['cashier_name'])

        line_in = exchange.statement_line_in_id
        line_out = exchange.statement_line_out_id
        self.assertEqual(line_in.amount, 100.0)
        self.assertFalse(line_in.foreign_currency_id)
        self.assertEqual(line_in.pos_session_id, session)
        self.assertEqual(line_out.amount, -96.82)
        self.assertEqual(line_out.foreign_currency_id, self.fx)
        self.assertEqual(line_out.amount_currency, -213.0)
        for line in (line_in, line_out):
            self.assertIn(self.commission_account, line.move_id.line_ids.account_id)
        commission_lines = (line_in.move_id.line_ids + line_out.move_id.line_ids).filtered(
            lambda l: l.account_id == self.commission_account)
        self.assertEqual(self.main.round(-sum(commission_lines.mapped('balance'))), 3.18)

        # Drawers: 213 EUR left the foreign drawer, 100 entered the main one.
        self.assertEqual(self.pos_config._nm_currency_balance(self.fx), 287.0)
        detail = session.currency_detail_ids.filtered(lambda d: d.currency_id == self.fx)
        self.assertEqual(detail.cash_moves_amount, -213.0)
        self._refresh_journal()
        data = session.get_closing_control_data()
        fx_data = next(d for d in data['multicurrency_details'] if d['currency_id'] == self.fx.id)
        self.assertEqual(fx_data['amount'], 287.0)
        self.assertIn(-213.0, [m['amount'] for m in fx_data['moves']])
        self.assertEqual(data['default_cash_details']['amount'], 100.0)
        summary = data['nm_exchange_summary']
        self.assertEqual(summary['count'], 1)
        self.assertEqual(summary['commission'], 3.18)
        self.assertEqual(summary['operations'][0]['name'], exchange.name)
        self.assertEqual(session.nm_exchange_count, 1)
        self.assertEqual(session.nm_exchange_commission, 3.18)
        self.assertEqual(self.pos_config.nm_exchange_count, 1)

        # Closing at the expected amounts: no difference anywhere.
        self._close(session, main=100.0, fx=287.0)
        self.assertEqual(detail.difference_amount, 0.0)
        self.assertEqual(session.state, 'closed')
        # Report block.
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=session.ids)
        self.assertEqual(report['nm_exchange']['count'], 1)
        self.assertEqual(report['nm_exchange']['commission'], 3.18)
        values = self.env['report.point_of_sale.report_saledetails']._get_report_values(session.ids)
        self.assertIn('nm_exchange', values)
        # Position report sees the drawer at 287.
        self.env.flush_all()
        position = self.env['pos.nm.currency.position'].search([
            ('journal_id', '=', self.cash_journal.id), ('currency_id', '=', self.fx.id)])
        self.assertEqual(position.balance, 287.0)

    def test_exchange_foreign_to_main(self):
        session = self._open(fx=0.0)
        receipt = self.env['pos.nm.exchange'].create_from_ui(session.id, self.fx.id, 220.0, self.main.id)
        exchange = self.env['pos.nm.exchange'].browse(receipt['id'])
        self.assertEqual(exchange.amount_out, 97.0)
        self.assertEqual(exchange.commission, 3.0)
        self.assertEqual(exchange.statement_line_in_id.amount_currency, 220.0)
        self.assertEqual(exchange.statement_line_in_id.amount, 100.0)
        self.assertEqual(exchange.statement_line_out_id.amount, -97.0)
        self.assertFalse(exchange.statement_line_out_id.foreign_currency_id)
        self.assertEqual(self.pos_config._nm_currency_balance(self.fx), 220.0)
        self._close(session, main=-97.0, fx=220.0)

    def test_exchange_checks(self):
        session = self._open(fx=100.0)
        Exchange = self.env['pos.nm.exchange']
        # Not enough notes in the drawer.
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        # Customer required above the threshold.
        self.pos_config.nm_exchange_customer_threshold = 30.0
        quote = self._quote(self.main, 40.0, self.fx)
        self.assertTrue(quote['customer_required'])
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 40.0, self.fx.id)
        receipt = Exchange.create_from_ui(session.id, self.main.id, 40.0, self.fx.id, self.partner_id)
        self.assertEqual(Exchange.browse(receipt['id']).partner_id.id, self.partner_id)
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
