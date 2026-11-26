# -*- coding: utf-8 -*-

import importlib.util
from datetime import timedelta
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http.dispatcher import serialize_exception
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger
from odoo.tools.misc import file_path
from odoo.addons.point_of_sale.tests.test_pos_accounting import TestPosAccounting
from odoo.addons.pos_nm_currency_exchange import _nm_check_parent_version
from odoo.addons.pos_nm_currency_exchange.models.pos_currency_setting import nm_default_sell_margin
from odoo.addons.pos_nm_currency_exchange.models.pos_exchange import QUOTE_CHANGED, NmQuoteChangedError


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

    def _backdate(self, exchange, date):
        """Move an operation in time behind the ORM (the register refuses
        to change a hashed operation), and hash it again in place."""
        self.env.cr.execute("UPDATE pos_nm_exchange SET date = %s WHERE id = %s", [date, exchange.id])
        exchange.invalidate_recordset(['date'])
        new_hash = exchange._nm_compute_hash(exchange.register_previous_hash)
        self.env.cr.execute("UPDATE pos_nm_exchange SET register_hash = %s WHERE id = %s", [new_hash, exchange.id])
        exchange.invalidate_recordset(['register_hash'])

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
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, False, note='tourist')
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

    def test_drawer_check_with_foreign_change(self):
        """Change handed back in EUR in a sale (a negative EUR cash payment)
        leaves fewer EUR notes for the counter: the quote and the operation
        are checked against the drawer less that change."""
        session = self._open(fx=30.0, main=0.0)
        Exchange = self.env['pos.nm.exchange']
        # 13 main: commission 3, 10 x 2 / 1.1 = 18.18 -> 18 EUR, enough in the 30 counted.
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 13.0, self.fx.id)
        self.assertEqual(quote['amount_out'], 18.0)
        self.assertFalse(quote['drawer_error'])
        # A sale of 10.60 paid 20 in the main currency, 9.40 handed back as 18.80 EUR.
        order = self.create_pos_order(
            payment_method=[
                [self.cash_pm, {'amount': 20.0}],
                [self.cash_pm, {'amount': -9.4, 'foreign_currency_id': self.fx.id, 'amount_currency': -18.8}],
            ],
            products=[[self.product_6, {}]],
        )
        self.assertEqual(order.state, 'paid')
        self.assertEqual(session._nm_expected_cash(self.fx), 11.2)
        self.assertEqual(session._nm_expected_cash(self.main), 20.0)
        # The 18 EUR no longer are in the drawer: shown and refused.
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 13.0, self.fx.id)
        self.assertEqual(quote['drawer_balance_formatted'], self.fx.format(11.2))
        self.assertIn('cannot be handed back', quote['drawer_error'])
        with self.assertRaisesRegex(UserError, 'cannot be handed back'):
            Exchange.create_from_ui(session.id, self.main.id, 13.0, self.fx.id)
        # 9 main hand back 10 EUR of the 11.20 left.
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 9.0, self.fx.id)['id'])
        self.assertEqual(exchange.amount_out, 10.0)
        self.assertAlmostEqual(session._nm_expected_cash(self.fx), 1.2, places=2)
        self.assertEqual(session._nm_expected_cash(self.main), 29.0)
        self._close(session, main=29.0, fx=1.2)

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
        with self.assertRaisesRegex(UserError, 'quote changed') as caught:
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, amount_out=quote['amount_out'])
        self.assertFalse(Exchange.search([('session_id', '=', session.id)]))
        # The register tells this refusal from the others by a code sent
        # with the error, not by its translated text.
        self.assertIsInstance(caught.exception, NmQuoteChangedError)
        data = serialize_exception(caught.exception)
        self.assertEqual(data['context'], {'nm_exchange_error': QUOTE_CHANGED, 'amount_out': 184.0, 'quoted': 176.0})
        # The other refusals carry no such code.
        with self.assertRaises(UserError) as caught:
            Exchange.create_from_ui(session.id, self.main.id, 0.0, self.fx.id, amount_out=quote['amount_out'])
        self.assertNotIsInstance(caught.exception, NmQuoteChangedError)
        self.assertEqual(serialize_exception(caught.exception)['context'], {})
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
        again = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, uuid='nm-uuid-1',
                                        amount_out=176.0)
        self.assertEqual(again, receipt)
        # Not when the cashier changed the popup in between: another amount,
        # currency, amount handed back or customer is another operation.
        for args, kwargs in (
            ((self.main.id, 50.0, self.fx.id), {}),
            ((self.fx.id, 100.0, self.main.id), {}),
            ((self.main.id, 100.0, self.fx.id), {'amount_out': 175.0}),
            ((self.main.id, 100.0, self.fx.id, self.partner_id), {}),
        ):
            with self.assertRaisesRegex(UserError, 'already recorded as %s' % receipt['name']):
                Exchange.create_from_ui(session.id, *args, uuid='nm-uuid-1', **kwargs)
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
        self._backdate(earlier, fields.Datetime.now() - timedelta(days=1))
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
        self.assertIn('1 operation<', html)
        self.assertIn('1 cancelled operation: %s' % cancelled.name, html)
        self.assertNotIn('1 operations', html)

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
        self._backdate(first, fields.Datetime.now() - timedelta(days=8))
        receipt = Exchange.create_from_ui(session.id, self.main.id, 900.0, self.fx.id, customer.id)
        self.assertEqual(Exchange.browse(receipt['id']).linked_value, 900.0)
        self.assertFalse(receipt['id_document'])
        # A cancelled operation does not count either.
        Exchange.browse(receipt['id']).with_user(self.env.user).action_cancel()
        self.assertEqual(Exchange._nm_linked_value(self.pos_config, 900.0, customer), 900.0)
        # An operation at another point of sale of the company counts, in
        # the currency of this one: 11900 XPF are worth 100.
        xpf = self.setup_other_currency('XPF', rates=[('1900-01-01', 119.0)])
        journal = self.env['account.journal'].create({
            'name': 'NM XPF Sales', 'code': 'NMXPF', 'type': 'general', 'currency_id': xpf.id})
        xpf_config = self.env['pos.config'].create({
            'name': 'NM XPF Shop', 'journal_id': journal.id, 'payment_method_ids': [(6, 0, [])]})
        xpf_session = self.env['pos.session'].create({'config_id': xpf_config.id, 'user_id': self.env.uid})
        self.env['pos.nm.exchange'].sudo().create({
            'session_id': xpf_session.id, 'partner_id': customer.id, 'currency_in_id': self.fx.id,
            'currency_out_id': xpf.id, 'amount_in': 100.0, 'amount_out': 11400.0, 'value_in': 11900.0,
            'value_out': 11400.0, 'commission': 500.0, 'rate_margin': 0.0})
        self.assertEqual(Exchange._nm_linked_value(self.pos_config, 900.0, customer), 1000.0)

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
        with self.assertRaisesRegex(UserError, 'Invalid date'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id,
                                    document=self._document(birthdate='17/05/1980'))
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
        # The personal data is not copied with the contact.
        self.assertFalse(customer.copy().nm_id_document_number)

        # The change is logged on the customer, with the masked number.
        message = customer.message_ids[0]
        self.assertIn(receipt['name'], message.body)
        self.assertIn('Passport ****4567', message.body)
        self.assertNotIn('AB1234567', message.body)
        # The register prefills the document of the customer, masked, without
        # the personal data.
        loaded = Exchange.get_customer_document(self.pos_config.id, customer.id)
        self.assertEqual(loaded, {
            'type': 'passport', 'number_masked': '****4567', 'country_id': self.env.ref('base.fr').id,
            'expiry': self._document()['expiry'], 'no_expiry': False})
        types = self.pos_config._load_pos_data_read(self.pos_config, self.pos_config)[0]['_nm_id_document_types']
        self.assertIn('passport', dict(types))
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
        # The register only reads the end of the number, at a point of sale
        # whose counter asks for identity documents.
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        with self.assertRaisesRegex(UserError, 'does not ask for identity documents'):
            Exchange.get_customer_document(self.pos_config.id, customer.id)
        self.pos_config.nm_exchange_document_threshold = 1000.0
        self.assertEqual(Exchange.get_customer_document(self.pos_config.id, customer.id)['number_masked'], '****ET99')
        self.pos_config.nm_exchange_enabled = False
        with self.assertRaisesRegex(UserError, 'disabled'):
            Exchange.get_customer_document(self.pos_config.id, customer.id)

    def test_identity_document_confirmed(self):
        """The register sends the document with the fields left empty that it
        does not show: the number, nationality and date of birth recorded on
        the customer are kept for the same document. A new document keeps
        only the personal data. The contact of an internal user, even
        archived, is changed by a manager only; a portal customer's is
        saved."""
        self.pos_config.write({'nm_exchange_document_threshold': 50.0})
        session = self._open(fx=10000.0)
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        customer = self.env['res.partner'].create({'name': 'NM Returning Customer', **{
            'nm_id_document_type': 'passport', 'nm_id_document_number': 'AB1234567',
            'nm_id_document_expiry': fields.Date.today() - timedelta(days=1),
            'nm_nationality_id': self.env.ref('base.fr').id, 'nm_birthdate': '1980-05-17'}})
        renewed = str(fields.Date.today() + timedelta(days=30))
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id, document={
            'type': 'passport', 'number': '', 'expiry': renewed})
        exchange = Exchange.browse(receipt['id']).with_user(self.env.user)
        self.assertEqual(exchange.id_document_number, 'AB1234567')
        self.assertEqual(exchange.id_birthdate, fields.Date.to_date('1980-05-17'))
        self.assertEqual(str(customer.nm_id_document_expiry), renewed)
        # The same document again: the contact is not written or logged.
        messages = customer.message_ids
        Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id, document={
            'type': 'passport', 'number': '', 'expiry': renewed})
        self.assertEqual(customer.message_ids, messages)
        # Another document: its number is required, its expiry is not taken
        # from the passport.
        with self.assertRaisesRegex(UserError, 'type and the number'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id, document={
                'type': 'id_card', 'number': '', 'expiry': renewed})
        with self.assertRaisesRegex(UserError, 'expiry date'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id, document={
                'type': 'id_card', 'number': 'ID-998877'})
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id, document={
            'type': 'id_card', 'number': 'ID-998877', 'expiry': renewed})
        self.assertEqual(receipt['id_document'], 'Identity Card ****8877')
        self.assertEqual(customer.nm_id_document_number, 'ID-998877')
        self.assertEqual(customer.nm_nationality_id, self.env.ref('base.fr'))

        # The contact of a user: the cashier does not overwrite it.
        user_partner = new_test_user(self.env, login='nm_exchange_employee', groups='base.group_user').partner_id
        user_partner.write({'nm_id_document_type': 'passport', 'nm_id_document_number': 'ADMIN0001',
                            'nm_id_document_expiry': renewed})
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, user_partner.id, document={
            'type': 'passport', 'number': 'FORGED001', 'expiry': renewed})
        self.assertEqual(receipt['id_document'], 'Passport ****D001')
        self.assertEqual(user_partner.nm_id_document_number, 'ADMIN0001')
        # An archived employee keeps the protection.
        user_partner.user_ids.active = False
        Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, user_partner.id, document={
            'type': 'passport', 'number': 'FORGED002', 'expiry': renewed})
        self.assertEqual(user_partner.nm_id_document_number, 'ADMIN0001')
        # A customer with a portal account is a customer: the document is saved.
        portal_partner = new_test_user(self.env, login='nm_exchange_portal', groups='base.group_portal').partner_id
        Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, portal_partner.id, document={
            'type': 'passport', 'number': 'PORTAL001', 'expiry': renewed})
        self.assertEqual(portal_partner.nm_id_document_number, 'PORTAL001')
        self.assertIn('****L001', portal_partner.message_ids[0].body)

    def test_identity_document_no_expiry(self):
        """An older document without expiry date is accepted once "No
        expiry date" is ticked: saved on the customer, frozen on the
        operation, given back to the register and shown in the register of
        operations. An expiry date typed later clears the box; an expired
        document is still refused."""
        self.pos_config.write({'nm_exchange_document_threshold': 50.0})
        session = self._open(fx=10000.0)
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        customer = self.env['res.partner'].create({'name': 'NM Old Card Customer'})
        with self.assertRaisesRegex(UserError, 'expiry date'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id,
                                    document=self._document(type='id_card', expiry=''))
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id,
                                          document=self._document(type='id_card', expiry='', no_expiry=True))
        exchange = Exchange.browse(receipt['id']).with_user(self.env.user)
        self.assertTrue(exchange.id_document_no_expiry)
        self.assertFalse(exchange.id_document_expiry)
        self.assertTrue(customer.nm_id_document_no_expiry)
        self.assertFalse(customer.nm_id_document_expiry)
        loaded = Exchange.get_customer_document(self.pos_config.id, customer.id)
        self.assertEqual((loaded['expiry'], loaded['no_expiry']), (False, True))
        # Confirmed without the box (the register sends the fields empty):
        # the document of the customer, without expiry date, is kept.
        messages = customer.message_ids
        second = Exchange.browse(Exchange.create_from_ui(
            session.id, self.main.id, 100.0, self.fx.id, customer.id,
            document={'type': 'id_card', 'number': ''})['id']).with_user(self.env.user)
        self.assertTrue(second.id_document_no_expiry)
        self.assertEqual(customer.message_ids, messages)
        # Without a document sent, the one of the customer is used.
        Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id)
        # Both sent: the box wins, the expiry date is not kept.
        both = Exchange.browse(Exchange.create_from_ui(
            session.id, self.main.id, 100.0, self.fx.id, customer.id,
            document=self._document(type='id_card', no_expiry=True))['id']).with_user(self.env.user)
        self.assertFalse(both.id_document_expiry)

        # A renewed card with an expiry date clears the box.
        renewed = str(fields.Date.today() + timedelta(days=30))
        Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id,
                                document={'type': 'id_card', 'number': '', 'expiry': renewed})
        self.assertFalse(customer.nm_id_document_no_expiry)
        self.assertEqual(str(customer.nm_id_document_expiry), renewed)
        # Expired: refused even with the box ticked on the contact.
        customer.write({'nm_id_document_expiry': fields.Date.today() - timedelta(days=1),
                        'nm_id_document_no_expiry': True})
        self.assertIn('expired', Exchange._nm_document_error(Exchange._nm_document_values(customer)))

        # The register of operations says so.
        now = fields.Datetime.now()
        data = {'date_start': fields.Datetime.to_string(now - timedelta(hours=1)),
                'date_stop': fields.Datetime.to_string(now + timedelta(hours=1)), 'config_ids': self.pos_config.ids}
        values = self.env['report.pos_nm_currency_exchange.report_exchange_register']._get_report_values([], data)
        row = next(op for op in values['operations'] if op['name'] == exchange.name)
        self.assertTrue(row['document_no_expiry'])
        html = self._render('pos_nm_currency_exchange.action_report_exchange_register', [], data=data)
        self.assertIn('No expiry date', html)

    def test_linked_value_not_shown(self):
        """The quote gives the exchanges of the customer over the period only
        when they make the customer or the document required."""
        self.pos_config.write({'nm_exchange_document_threshold': 1000.0, 'nm_exchange_linked_days': 7})
        session = self._open(fx=10000.0)
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        customer = self.env['res.partner'].create({'name': 'NM Private Volume'})
        Exchange.create_from_ui(session.id, self.main.id, 500.0, self.fx.id, customer.id)
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 10.0, self.fx.id, customer.id)
        self.assertFalse(quote['document_required'])
        self.assertEqual(quote['linked_value'], 10.0)
        self.assertNotIn('threshold_exceeded', quote)
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 600.0, self.fx.id, customer.id)
        self.assertTrue(quote['document_required'])
        self.assertEqual(quote['linked_value'], 1100.0)

    def _run_migration(self, name):
        path = file_path(f'pos_nm_currency_exchange/migrations/20.0.2.0.0/{name}.py')
        spec = importlib.util.spec_from_file_location('odoo.addons.pos_nm_currency_exchange.nm_migration', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.env.cr, '20.0.1.1.0')
        self.env.invalidate_all()

    def test_migration_missing_leg(self):
        """An operation of 20.0.1.x whose handed-back line was deleted is
        reported once on upgrade, on the operation."""
        session = self._open(fx=500.0)
        Exchange = self.env['pos.nm.exchange']
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        self.env.flush_all()
        self.env.cr.execute("UPDATE pos_nm_exchange SET statement_line_out_id = NULL WHERE id = %s", [exchange.id])
        self.env.invalidate_all()
        before = len(exchange.message_ids)
        with self.assertLogs('odoo.addons.pos_nm_currency_exchange', level='WARNING'):
            self._run_migration('post-migrate')
        self.assertEqual(len(exchange.message_ids), before + 1)
        self.assertIn('handed back', exchange.message_ids[0].body)
        # Run again: still logged, not posted twice.
        with self.assertLogs('odoo.addons.pos_nm_currency_exchange', level='WARNING'):
            self._run_migration('post-migrate')
        self.assertEqual(len(exchange.message_ids), before + 1)

    def test_migration_sell_margin(self):
        """A negative cash rate margin keeps its sell rate: -2 % handed back
        0.98 of the rate of Odoo, the sell margin 2.04 % does too."""
        self.setting.margin_percent = -2.0
        self.env.flush_all()
        self.env.cr.execute("UPDATE pos_nm_currency_setting SET exchange_sell_margin_percent = NULL WHERE id = %s",
                            [self.setting.id])
        self._run_migration('pre-migrate')
        self.assertAlmostEqual(self.setting.exchange_sell_margin_percent, 2.0408, places=4)
        self.assertAlmostEqual(self.pos_config._nm_exchange_sell_rate(self.fx), 2.0 * 0.98, places=6)

    def test_default_sell_margin(self):
        """A currency added after the upgrade starts from the sell margin the
        upgrade gives: its cash rate margin, -m / (1 + m / 100) for a
        negative one; an explicit sell margin is kept. The form follows the
        cash rate margin while the currency is not saved, never after."""
        self.assertEqual(nm_default_sell_margin(10.0), 10.0)
        self.assertEqual(nm_default_sell_margin(0.0), 0.0)
        self.assertAlmostEqual(nm_default_sell_margin(-2.0), 2.0 / 0.98, places=10)
        # -100 % or less is refused by the constraint of the cash rate
        # margin, not by a division by zero.
        self.assertEqual(nm_default_sell_margin(-100.0), 0.0)
        self.assertEqual(nm_default_sell_margin(-150.0), 0.0)
        with self.assertRaises(ValidationError):
            self._add_cash_currency('NOK', 11.0, margin_percent=-100.0)
        chf =self._add_cash_currency('CHF', 0.8, margin_percent=4.0)
        jpy = self._add_cash_currency('JPY', 150.0, margin_percent=-2.0)
        gbp = self._add_cash_currency('GBP', 0.85, margin_percent=4.0, exchange_sell_margin_percent=1.5)
        sek = self._add_cash_currency('SEK', 11.0)
        margins = {setting.currency_id: setting.exchange_sell_margin_percent
                   for setting in self.pos_config.nm_currency_setting_ids}
        self.assertEqual(margins[chf], 4.0)
        self.assertAlmostEqual(margins[jpy], 2.0408, places=4)
        self.assertEqual(margins[gbp], 1.5)
        self.assertEqual(margins[sek], 0.0)
        # Same sell rate as the upgrade: 150 x 0.98 for -2 %.
        self.assertAlmostEqual(self.pos_config._nm_exchange_sell_rate(jpy), 150.0 * 0.98, places=2)
        # The form of a new currency follows the cash rate margin.
        Setting = self.env['pos.nm.currency.setting']
        result = Setting.onchange({'margin_percent': 6.0, 'exchange_sell_margin_percent': 0.0},
                                  ['margin_percent'], {'margin_percent': {}, 'exchange_sell_margin_percent': {}})
        self.assertEqual(result['value']['exchange_sell_margin_percent'], 6.0)
        # A saved currency keeps its sell margin.
        setting = self.pos_config._nm_get_currency_setting(gbp)
        result = setting.onchange({'margin_percent': 6.0}, ['margin_percent'],
                                  {'margin_percent': {}, 'exchange_sell_margin_percent': {}})
        self.assertNotIn('exchange_sell_margin_percent', result.get('value', {}))
        # Sell margin help documents it.
        self.assertIn('Cash Rate Margin', Setting._fields['exchange_sell_margin_percent'].help)

    def test_parent_version_guard(self):
        """Installing or upgrading on POS Multi-Currency Cash older than
        20.0.2.1.0 is refused: the register would not load."""
        _nm_check_parent_version(self.env)
        self.env.cr.execute(
            "UPDATE ir_module_module SET latest_version = '20.0.2.0.0' WHERE name = 'pos_nm_multicurrencies'")
        with self.assertRaisesRegex(UserError, '20.0.2.1.0 or later'):
            _nm_check_parent_version(self.env)

    def test_counter_settings_access(self):
        """The POS users read the point of sale but do not change the
        settings of the counter: they control the cashiers."""
        manager = new_test_user(
            self.env, login='nm_exchange_manager', groups='point_of_sale.group_pos_manager',
            company_id=self.company.id)
        for vals in ({'nm_exchange_document_threshold': 0.0}, {'nm_exchange_customer_always': False},
                     {'nm_exchange_linked_days': 0}, {'nm_exchange_income_account_id': self.profit_account.id},
                     {'nm_exchange_enabled': False}):
            with self.assertRaises(AccessError):
                self.pos_config.with_user(self.pos_user).write(vals)
        self.pos_config.with_user(manager).write({'nm_exchange_document_threshold': 500.0})
        self.assertEqual(self.pos_config.nm_exchange_document_threshold, 500.0)

    # ------------------------------------------------------------------
    # Receipt, reprint, rate board and register
    # ------------------------------------------------------------------

    def _render(self, report_ref, docids, data=None):
        html, _format = self.env['ir.actions.report']._render_qweb_html(report_ref, docids, data=data)
        return html.decode()

    def test_receipt_content(self):
        """The receipt prints the header and footer of the POS receipts, the
        licence number, the operation from the point of view of the shop and
        the time with the seconds; the PDF of the operation has the same
        content, with the cancellation once cancelled."""
        self.pos_config.write({
            'receipt_header': 'NM Header Line',
            'receipt_footer': 'NM Footer Line',
            'nm_exchange_licence': 'LIC-2026-42',
        })
        chf = self._add_cash_currency('CHF', 0.8, change_rounding=1.0)
        session = self._open(fx=500.0, main=100.0, counts={chf: 100.0})
        Exchange = self.env['pos.nm.exchange']
        sale = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        purchase = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)['id'])
        cross = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 220.0, chf.id)['id'])
        self.assertEqual((sale.operation_type, purchase.operation_type, cross.operation_type),
                         ('sale', 'purchase', 'cross'))

        receipt = sale._nm_receipt_data()
        self.assertEqual(receipt['operation_type'], 'Sale of foreign currency')
        self.assertRegex(receipt['date'], r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
        self.assertEqual(receipt['licence'], 'LIC-2026-42')
        self.assertEqual((receipt['receipt_header'], receipt['receipt_footer']), ('NM Header Line', 'NM Footer Line'))
        self.assertFalse(receipt['cancelled'] or receipt['copy'])
        self.assertEqual(purchase._nm_receipt_data()['operation_type'], 'Purchase of foreign currency')
        self.assertEqual(cross._nm_receipt_data()['operation_type'], 'Cross exchange')

        html = self._render('pos_nm_currency_exchange.action_report_pos_nm_exchange', sale.ids)
        for text in ('NM Header Line', 'NM Footer Line', 'LIC-2026-42', 'Sale of foreign currency', sale.name,
                     receipt['date'], sale.rate_label, self.main.format(3.2)):
            self.assertIn(text, html)
        self.assertNotIn('CANCELLED', html)

        sale.action_cancel()
        html = self._render('pos_nm_currency_exchange.action_report_pos_nm_exchange', sale.ids)
        self.assertIn('CANCELLED', html)
        self.assertIn(sale._nm_receipt_data()['cancel_date'], html)

    def test_reprint_rpc(self):
        """The register lists the operations of the session and prints their
        receipt again, as a copy, cancelled when cancelled since."""
        session = self._open(fx=500.0, main=100.0)
        Exchange = self.env['pos.nm.exchange']
        first = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        second = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)['id'])
        first.action_cancel()
        cashier = Exchange.with_user(self.pos_user)
        operations = cashier.get_session_operations(session.id)
        self.assertEqual([op['name'] for op in operations], [second.name, first.name])
        self.assertEqual([op['cancelled'] for op in operations], [False, True])
        self.assertEqual(operations[0]['operation_type'], 'Purchase of foreign currency')
        receipt = cashier.get_receipt(first.id)
        self.assertTrue(receipt['copy'])
        self.assertTrue(receipt['cancelled'])
        self.assertEqual(receipt['amount_out'], self.fx.format(176.0))
        self.assertFalse(cashier.get_receipt(second.id)['cancelled'])
        with self.assertRaises(UserError):
            cashier.get_receipt(0)

    def test_send_by_email(self):
        """Send by E-mail: the composer with the template sends the receipt
        to the customer, with the PDF attached."""
        session = self._open(fx=500.0)
        customer = self.env['res.partner'].create({'name': 'NM Mail Customer', 'email': 'nm.customer@example.com'})
        Exchange = self.env['pos.nm.exchange']
        exchange = Exchange.browse(
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id)['id'])
        # Nobody follows the operation: the e-mail goes to the customer only.
        self.assertFalse(exchange.message_follower_ids)
        action = exchange.action_send_mail()
        self.assertEqual(action['res_model'], 'mail.compose.message')
        composer = self.env['mail.compose.message'].with_context(action['context']).create({})
        self.assertIn(customer, composer.partner_ids)
        self.assertEqual(len(composer.attachment_ids), 1)
        composer.action_send_mail()
        message = exchange.message_ids.filtered(lambda m: customer in m.partner_ids)
        self.assertEqual(len(message), 1)
        self.assertEqual(len(message.attachment_ids), 1)
        self.assertIn(exchange.name.replace('/', '_'), message.attachment_ids.name)

    def test_chatter_log(self):
        """The changes of the note and the cancellation are logged on the
        operation."""
        session = self._open(fx=500.0, main=100.0)
        Exchange = self.env['pos.nm.exchange']
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        before = len(exchange.message_ids)
        exchange.note = 'checked'
        self.env.flush_all()
        self.assertEqual(len(exchange.message_ids), before + 1)
        exchange.action_cancel()
        self.env.flush_all()
        self.assertEqual(len(exchange.message_ids), before + 2)

    def test_rate_board(self):
        """The rate board gives, for EUR, the figures of the quote: 1 EUR
        bought is worth 1 / 2.2 = 0.45 (the value of 1 EUR received),
        100 EUR bought hand back the amount of their quote; 1 EUR sold is
        worth 1.1 / 2 = 0.55, 100 EUR sold cost the smallest amount whose
        quote hands them back."""
        self.pos_config.nm_exchange_licence = 'LIC-2026-42'
        board = self.env['pos.nm.exchange'].with_user(self.pos_user).get_rate_board(self.pos_config.id)
        self.assertEqual(board['licence'], 'LIC-2026-42')
        row, = board['rows']
        self.assertEqual(row['currency'], self.fx.name)
        self.assertEqual(row['amount'], 100.0)
        self.assertEqual(self.main.round(row['buy_unit']), self._quote(self.fx, 1.0, self.main)['value_in'])
        self.assertEqual(row['buy_amount'], self._quote(self.fx, 100.0, self.main)['amount_out'])
        self.assertEqual(row['buy_amount'], 42.45)  # 100 EUR worth 45.45, commission 3
        Exchange = self.env['pos.nm.exchange']
        one_unit = Exchange._nm_reverse_amount_in(self.pos_config, self.main, self.fx, 1.0)
        self.assertEqual(self.main.round(row['sell_unit']), self._quote(self.main, one_unit, self.fx)['value_out'])
        self.assertEqual(self.main.round(row['sell_unit']), 0.55)
        self.assertEqual(self._quote(self.main, row['sell_amount'], self.fx)['amount_out'], 100.0)
        self.assertLess(self._quote(self.main, row['sell_amount'] - 0.01, self.fx)['amount_out'], 100.0)
        self.assertEqual(row['sell_amount'], 58.0)  # 55 + 3 of commission
        # One sentence, translated as a whole.
        self.assertEqual(row['commission_label'], '2.00 %% + %s, min. %s' % (
            self.main.format(1.0), self.main.format(3.0)))
        # The 4 decimals of the percentage are kept: 0.125 does not read 0.13.
        self.setting.exchange_commission_percent = 0.125
        self.assertTrue(self.pos_config._nm_rate_board()['rows'][0]['commission_label'].startswith('0.125 % +'))
        # The parts that are zero are left out.
        label = lambda: self.pos_config._nm_commission_label(self.setting)
        self.setting.exchange_commission_fixed = 0.0
        self.assertEqual(label(), '0.125 %%, min. %s' % self.main.format(3.0))
        self.setting.exchange_commission_min = 0.0
        self.assertEqual(label(), '0.125 %')
        self.setting.exchange_commission_percent = 0.0
        self.assertEqual(label(), 'No commission')
        self.setting.exchange_commission_fixed = 1.0
        self.assertEqual(label(), self.main.format(1.0))
        self.setting.write({'exchange_commission_percent': 2.0, 'exchange_commission_min': 3.0})

        html = self._render('pos_nm_currency_exchange.action_report_exchange_rates', self.pos_config.ids)
        for text in ('Exchange Rates', 'LIC-2026-42', 'We buy', 'We sell', row['buy_rate_label'],
                     row['sell_rate_label'], row['buy_amount_formatted'], row['sell_amount_formatted'],
                     ', min. '):
            self.assertIn(text, html)
        action = self.env['res.config.settings'].with_context(discard_logo_check=True).create(
            {'pos_config_id': self.pos_config.id}).action_nm_print_rate_board()
        self.assertEqual(action['report_name'], 'pos_nm_currency_exchange.report_exchange_rates')

    def test_rate_board_amount(self):
        """The typical amount is the power of 10 nearest to 100 units of the
        currency of the point of sale."""
        xpf = self._add_cash_currency('XPF', 119.33)
        self.assertEqual(self.pos_config._nm_board_amount(xpf), 10000.0)
        self.assertEqual(self.pos_config._nm_board_amount(self.fx), 100.0)

    def test_rate_board_amount_steps(self):
        """The typical amount is rounded to the coins the counter takes and
        hands back: with 3 CHF accepted (Payment Rounding) and 0.20 CHF
        handed back (Change Rounding), 99 CHF instead of 100, which is not a
        multiple of 3. The board figures are those of the quote for 99 CHF,
        and the counter records both operations of the board as shown."""
        chf = self._add_cash_currency('CHF', 0.8, margin_percent=4.0, payment_rounding=3.0, change_rounding=0.2,
                                      exchange_commission_percent=1.0)
        Exchange = self.env['pos.nm.exchange']
        self.assertEqual(Exchange._nm_payment_step(self.pos_config, chf), 3.0)
        self.assertEqual(Exchange._nm_change_step(self.pos_config, chf), 0.2)
        row = next(row for row in self.pos_config._nm_rate_board()['rows'] if row['currency_id'] == chf.id)
        self.assertEqual(row['amount'], 99.0)
        self.assertEqual(row['amount_formatted'], chf.format(99.0))
        # A multiple of both steps: no coin warning, nothing rounded away.
        for step in (3.0, 0.2):
            units = row['amount'] / step
            self.assertAlmostEqual(units, round(units), places=6)
        # The figures of the quote.
        self.assertEqual(row['buy_amount'], self._quote(chf, 99.0, self.main)['amount_out'])
        self.assertEqual(self._quote(self.main, row['sell_amount'], chf)['amount_out'], 99.0)
        # Recorded as shown on the board.
        session = self._open(main=500.0, counts={chf: 500.0})
        bought = Exchange.create_from_ui(session.id, chf.id, row['amount'], self.main.id,
                                         amount_out=row['buy_amount'])
        self.assertEqual(Exchange.browse(bought['id']).amount_out, row['buy_amount'])
        sold = Exchange.create_from_ui(session.id, self.main.id, row['sell_amount'], chf.id, amount_out=99.0)
        self.assertEqual(Exchange.browse(sold['id']).amount_out, 99.0)
        # The register popup shows the same board.
        board = Exchange.with_user(self.pos_user).get_rate_board(self.pos_config.id)
        self.assertIn(row, board['rows'])
        # A step larger than the amount: one step.
        self.pos_config._nm_get_currency_setting(chf).payment_rounding = 500.0
        self.assertEqual(self.pos_config._nm_board_amount(chf), 500.0)

    def test_exchange_register(self):
        """The register lists every operation of the period on the points of
        sale chosen, in the order of the references, the cancelled ones
        included with their status, with the frozen identity document and
        the totals per currency of the operations done."""
        self.pos_config.write({'nm_exchange_document_threshold': 50.0})
        session = self._open(fx=500.0, main=100.0)
        Exchange = self.env['pos.nm.exchange']
        customer = self.env['res.partner'].create({'name': 'NM Register Customer'})
        first = Exchange.browse(Exchange.create_from_ui(
            session.id, self.main.id, 100.0, self.fx.id, customer.id, document=self._document())['id'])
        second = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 22.0, self.main.id)['id'])
        third = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 44.0, self.main.id)['id'])
        second.action_cancel()

        now = fields.Datetime.now()
        wizard = self.env['pos.nm.exchange.register.wizard'].create({
            'date_start': now - timedelta(hours=1),
            'date_stop': now + timedelta(hours=1),
            'config_ids': self.pos_config.ids,
        })
        action = wizard.with_context(discard_logo_check=True).action_print()
        self.assertEqual(action['report_name'], 'pos_nm_currency_exchange.report_exchange_register')
        values = self.env['report.pos_nm_currency_exchange.report_exchange_register']._get_report_values(
            [], action['data'])
        self.assertEqual([op['name'] for op in values['operations']], [first.name, second.name, third.name])
        self.assertEqual([op['cancelled'] for op in values['operations']], [False, True, False])
        self.assertEqual(values['operations'][0]['document_number'], 'AB1234567')
        self.assertEqual(values['operations'][0]['customer'], 'NM Register Customer')
        self.assertEqual(values['operations'][0]['operation_type'], 'Sale of foreign currency')
        self.assertEqual(values['cancelled_count'], 1)
        totals = {total['currency']: total for total in values['totals']}
        # Done: 100 main for 176 EUR, 44 EUR for 17 main (worth 20, commission 3).
        self.assertEqual(totals[self.fx.name]['amount_in'], self.fx.format(44.0))
        self.assertEqual(totals[self.fx.name]['amount_out'], self.fx.format(176.0))
        self.assertEqual(totals[self.main.name]['amount_in'], self.main.format(100.0))
        self.assertEqual(totals[self.main.name]['amount_out'], self.main.format(17.0))
        self.assertEqual(totals[self.main.name]['commission'], self.main.format(first.commission + third.commission))
        self.assertEqual(totals[self.fx.name]['commission'], '')

        html = self._render('pos_nm_currency_exchange.action_report_exchange_register', [], data=action['data'])
        self.assertLess(html.index(first.name), html.index(second.name))
        self.assertLess(html.index(second.name), html.index(third.name))
        for text in ('Exchange Register', 'Cancelled', 'AB1234567', 'NM Register Customer',
                     'Sale of foreign currency', 'Purchase of foreign currency', first.rate_label,
                     self.main.format(first.commission + third.commission), '1 cancelled operation is listed'):
            self.assertIn(text, html)
        self.assertNotIn('cancelled operations are listed', html)
        # Another point of sale: nothing.
        other = self.pos_config.copy()
        values = self.env['report.pos_nm_currency_exchange.report_exchange_register']._get_report_values(
            [], {**action['data'], 'config_ids': other.ids})
        self.assertFalse(values['operations'])
        # The list of the register shows the cancelled operations too.
        register = self.env.ref('pos_nm_currency_exchange.action_pos_nm_exchange_register')
        self.assertNotIn('search_default_done', register.context or '')

    def test_manager_back_office(self):
        """A Point of Sale manager, not an administrator, e-mails the
        receipt, edits the note, prints the receipt, the rate board and the
        register."""
        session = self._open(fx=500.0)
        customer = self.env['res.partner'].create({'name': 'NM Manager Customer', 'email': 'nm.mgr@example.com'})
        Exchange = self.env['pos.nm.exchange']
        exchange = Exchange.browse(
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, customer.id)['id'])
        manager = new_test_user(self.env, login='nm_exchange_manager', groups='point_of_sale.group_pos_manager',
                                email='nm.manager@example.com')
        exchange = exchange.with_user(manager)
        exchange.note = 'checked'
        action = exchange.action_send_mail()
        composer = self.env['mail.compose.message'].with_user(manager).with_context(action['context']).create({})
        composer.action_send_mail()
        message = exchange.message_ids.filtered(lambda m: customer in m.partner_ids)
        self.assertEqual(len(message.attachment_ids), 1)
        report = self.env['ir.actions.report'].with_user(manager)
        html = report._render_qweb_html('pos_nm_currency_exchange.action_report_pos_nm_exchange', exchange.ids)[0]
        self.assertIn(exchange.name, html.decode())
        html = report._render_qweb_html('pos_nm_currency_exchange.action_report_exchange_rates',
                                        self.pos_config.ids)[0]
        self.assertIn('We buy', html.decode())
        now = fields.Datetime.now()
        wizard = self.env['pos.nm.exchange.register.wizard'].with_user(manager).create({
            'date_start': now - timedelta(hours=1), 'date_stop': now + timedelta(hours=1)})
        data = wizard.action_print()['data']
        html = report._render_qweb_html('pos_nm_currency_exchange.action_report_exchange_register', [], data=data)[0]
        self.assertIn(exchange.name, html.decode())
