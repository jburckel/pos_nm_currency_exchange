# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_nm_multicurrencies.tests.test_frontend import TestPosMulticurrencyUi


@tagged('post_install', '-at_install')
class TestPosCurrencyExchangeUi(TestPointOfSaleHttpCommon):
    """Register tour of the exchange counter."""

    def test_pos_currency_exchange_tour(self):
        """50 EUR received at the rate 0.87 (worth 57.47), 2% commission
        (1.15): 56.32 handed back in the main currency. The response of the
        first Confirm is lost: Confirm again returns the operation recorded,
        once. The receipt is printed again from Exchange Operations, the
        rates from Exchange Rates."""
        foreign_currency, cash_pm = TestPosMulticurrencyUi._setup_multicurrency(self, 60.0)
        commission_account = self.env['account.account'].create({
            'name': 'EX Tour Commissions', 'code': '999053', 'account_type': 'income_other'})
        self.main_pos_config.write({
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': commission_account.id,
            'nm_exchange_licence': 'LIC-TOUR-7',
            'receipt_header': 'Tour Header',
        })
        self.env['pos.nm.currency.setting'].create({
            'config_id': self.main_pos_config.id,
            'currency_id': foreign_currency.id,
            'exchange_commission_percent': 2.0,
            # 1 EUR coins: 50.5 EUR received shows a warning in the popup.
            'change_rounding': 1.0,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        TestPosMulticurrencyUi._start_tour(self, 'PosCurrencyExchangeTour')

        session.invalidate_recordset()
        self.assertEqual(session.state, 'closed')
        exchange = session.nm_exchange_ids
        self.assertEqual(len(exchange), 1)
        self.assertEqual(exchange.currency_in_id, foreign_currency)
        self.assertAlmostEqual(exchange.amount_in, 50.0, places=2)
        self.assertEqual(exchange.currency_out_id, self.main_pos_config.currency_id)
        self.assertAlmostEqual(exchange.value_in, 57.47, places=2)
        self.assertAlmostEqual(exchange.commission, 1.15, places=2)
        self.assertAlmostEqual(exchange.amount_out, 56.32, places=2)
        self.assertEqual(exchange.note, 'Tour')
        # Recorded by the server for the logged-in cashier.
        self.assertEqual(exchange.user_id, self.pos_user)
        self.assertEqual(exchange.cashier_name, self.pos_user.name)
        # 100 counted at opening plus the 50 received.
        self.assertAlmostEqual(self.main_pos_config._nm_currency_balance(foreign_currency), 150.0, places=2)
        # The rate margin shown by the closing popup: none at the rate of Odoo.
        self.assertEqual(exchange.rate_margin, 0.0)
        data = session.get_closing_control_data()
        self.assertEqual(data['nm_exchange_summary']['count'], 1)
        self.assertEqual(data['nm_exchange_summary']['rate_margin'], 0.0)
        # 100 counted in the main drawer at opening less the 56.32 handed back.
        self.assertAlmostEqual(data['default_cash_details']['amount'], 43.68, places=2)

    def test_pos_currency_exchange_reverse_tour(self):
        """XPF (no decimals, 119.33 for 1 main, 5 XPF coins) besides EUR, no
        commission: 25000 XPF typed in the popup give 209.50; the customer
        then wants 9998 XPF: 83.81 received (10001 XPF rounded down to 5),
        10000 XPF handed back and shown as such."""
        foreign_currency, cash_pm = TestPosMulticurrencyUi._setup_multicurrency(self, 60.0)
        xpf = self.env.ref('base.XPF')
        xpf.active = True
        self.env['res.currency.rate'].create({
            'name': '2024-01-01', 'currency_id': xpf.id, 'rate': 119.33, 'company_id': self.env.company.id})
        cash_pm.currency_ids = [(4, xpf.id)]
        self.env['pos.nm.currency.setting'].create({
            'config_id': self.main_pos_config.id, 'currency_id': xpf.id, 'change_rounding': 5.0})
        commission_account = self.env['account.account'].create({
            'name': 'EX Tour Commissions', 'code': '999053', 'account_type': 'income_other'})
        self.main_pos_config.write({
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': commission_account.id,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        TestPosMulticurrencyUi._start_tour(self, 'PosCurrencyExchangeReverseTour')

        first, second = session.nm_exchange_ids.sorted('id')
        self.assertEqual((first.currency_in_id, first.amount_in), (xpf, 25000.0))
        self.assertEqual((first.currency_out_id, first.amount_out), (self.main_pos_config.currency_id, 209.5))
        self.assertEqual((second.currency_in_id, second.amount_in), (self.main_pos_config.currency_id, 83.81))
        self.assertEqual((second.currency_out_id, second.amount_out), (xpf, 10000.0))
        # Nothing recorded from the refused EUR operation.
        self.assertEqual(len(session.nm_exchange_ids), 2)
        self.assertTrue(first.uuid and second.uuid and first.uuid != second.uuid)

    def test_pos_currency_exchange_document_tour(self):
        """Identity document required above 20: the expired document of the
        customer is refused in the popup, "No expiry date" hides the expiry
        date, the corrected one is saved on the customer and frozen on the
        operation. The quotes shown are stale (1 more handed back): the first
        Confirm is refused, a fresh quote is shown and confirmed by the
        cashier, once, at the amount of the server. A second operation ticks
        "No expiry date" on the document prefilled from the customer."""
        foreign_currency, cash_pm = TestPosMulticurrencyUi._setup_multicurrency(self, 60.0)
        commission_account = self.env['account.account'].create({
            'name': 'EX Tour Commissions', 'code': '999053', 'account_type': 'income_other'})
        self.main_pos_config.write({
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': commission_account.id,
            'nm_exchange_document_threshold': 20.0,
        })
        self.env['pos.nm.currency.setting'].create({
            'config_id': self.main_pos_config.id, 'currency_id': foreign_currency.id})
        customer = self.env['res.partner'].search([('name', '=', 'Partner Test 1')], limit=1)
        customer.write({
            'nm_id_document_type': 'passport',
            'nm_id_document_number': 'X1234567',
            'nm_id_document_expiry': '2020-01-31',
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        TestPosMulticurrencyUi._start_tour(self, 'PosCurrencyExchangeDocumentTour')

        exchange, second = session.nm_exchange_ids.sorted('id')
        self.assertEqual(len(session.nm_exchange_ids), 2)
        self.assertEqual(exchange.partner_id, customer)
        self.assertEqual(exchange.id_document_number, 'X1234567')
        self.assertEqual(str(exchange.id_document_expiry), '2099-12-31')
        self.assertFalse(exchange.id_document_no_expiry)
        # Recorded at the fresh quote of the server, not at the stale one.
        quote = self.env['pos.nm.exchange']._nm_quote(
            self.main_pos_config, foreign_currency, 50.0, self.main_pos_config.currency_id)
        self.assertEqual(quote['amount_out'], 57.47)
        self.assertEqual(exchange.amount_out, 57.47)
        # Second operation: "No expiry date" ticked, saved on the customer
        # (the expiry date cleared) and frozen on the operation.
        self.assertEqual(second.partner_id, customer)
        self.assertEqual(second.id_document_number, 'X1234567')
        self.assertTrue(second.id_document_no_expiry)
        self.assertFalse(second.id_document_expiry)
        self.assertTrue(customer.nm_id_document_no_expiry)
        self.assertFalse(customer.nm_id_document_expiry)
        # The first operation keeps its copy of the document.
        self.assertEqual(str(exchange.id_document_expiry), '2099-12-31')

    def test_pos_currency_exchange_no_account_tour(self):
        """Counter enabled without commission account: the register explains
        it instead of opening the popup."""
        TestPosMulticurrencyUi._setup_multicurrency(self, 60.0)
        self.main_pos_config.write({'nm_exchange_enabled': True, 'nm_exchange_income_account_id': False})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        TestPosMulticurrencyUi._start_tour(self, 'PosCurrencyExchangeNoAccountTour')
        self.assertFalse(session.nm_exchange_ids)

    def test_pos_currency_exchange_no_currency_tour(self):
        """Counter enabled without foreign currency on the cash payment
        method: the register explains it instead of opening the popup."""
        commission_account = self.env['account.account'].create({
            'name': 'EX Tour Commissions', 'code': '999053', 'account_type': 'income_other'})
        self.main_pos_config.write({
            'cash_control': True,
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': commission_account.id,
        })
        self.assertFalse(self.main_pos_config._get_cash_payment_method().currency_ids
                         - self.main_pos_config.currency_id)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        TestPosMulticurrencyUi._start_tour(self, 'PosCurrencyExchangeNoCurrencyTour')
        self.assertFalse(session.nm_exchange_ids)

    def test_pos_currency_exchange_employee_tour(self):
        """With the Employees module (pos_hr): the register sends the
        employee logged in, who is stored as the cashier of the operation
        and of its statement lines. Skipped without pos_hr."""
        if self.env['ir.module.module']._get('pos_hr').state != 'installed':
            self.skipTest("pos_hr is not installed")
        foreign_currency, cash_pm = TestPosMulticurrencyUi._setup_multicurrency(self, 60.0)
        commission_account = self.env['account.account'].create({
            'name': 'EX Tour Commissions', 'code': '999053', 'account_type': 'income_other'})
        employee = self.env['hr.employee'].sudo().create({'name': 'NM Tour Employee', 'company_id': self.env.company.id})
        self.main_pos_config.write({
            'module_pos_hr': True,
            'cashier_employee_ids': [(6, 0, employee.ids)],
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': commission_account.id,
        })
        self.env['pos.nm.currency.setting'].create({
            'config_id': self.main_pos_config.id, 'currency_id': foreign_currency.id})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosCurrencyExchangeEmployeeTour',
                        login="pos_user")

        exchange = session.nm_exchange_ids
        self.assertEqual(len(exchange), 1)
        self.assertEqual(exchange.amount_out, 57.47)
        self.assertEqual(exchange.cashier_name, 'NM Tour Employee')
        self.assertEqual(exchange.user_id, self.pos_user)
        lines = exchange.statement_line_in_id | exchange.statement_line_out_id
        self.assertEqual(lines.employee_id, employee)
        self.assertEqual(lines.partner_id, employee.work_contact_id)

    def test_pos_currency_exchange_note_stock_tour(self):
        """Notes of EUR tracked by denomination (50, 20, 10, 5), opening
        counted by coins/notes at the register: 1 x 50, 2 x 20, 1 x 10. 50 EUR
        received as 1 x 50, then 70 EUR handed back as the 1 x 50 and 1 x 20
        proposed: one note move per denomination, and 1 x 50, 1 x 20, 1 x 10
        left in the drawer, as counted at closing."""
        foreign_currency, cash_pm = TestPosMulticurrencyUi._setup_multicurrency(self, 60.0)
        commission_account = self.env['account.account'].create({
            'name': 'EX Tour Commissions', 'code': '999053', 'account_type': 'income_other'})
        self.main_pos_config.write({
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': commission_account.id,
            'nm_exchange_track_notes': True,
        })
        self.env['pos.nm.currency.setting'].create({
            'config_id': self.main_pos_config.id, 'currency_id': foreign_currency.id, 'change_rounding': 5.0})
        self.assertEqual(
            self.main_pos_config._load_pos_data_read(self.main_pos_config, self.main_pos_config)[0]['_nm_note_currency_ids'],
            [foreign_currency.id])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        session = self.main_pos_config.current_session_id
        TestPosMulticurrencyUi._start_tour(self, 'PosCurrencyExchangeNoteStockTour')

        session.invalidate_recordset()
        self.assertEqual(session.state, 'closed')
        detail = session.currency_detail_ids.filtered(lambda d: d.currency_id == foreign_currency)
        self.assertEqual(detail.opening_details, {'50': 1, '20': 2, '10': 1})
        self.assertEqual(detail.closing_details, {'50': 1, '20': 1, '10': 1})
        received, handed = session.nm_exchange_ids.sorted('id')
        self.assertEqual((received.currency_in_id, received.amount_in), (foreign_currency, 50.0))
        self.assertEqual((handed.currency_out_id, handed.amount_out), (foreign_currency, 70.0))
        moves = self.env['pos.nm.note.move'].search([('session_id', '=', session.id)])
        self.assertEqual(
            sorted((move.exchange_id.id, move.currency_id.id, move.value, move.quantity, move.origin) for move in moves),
            sorted([
                (received.id, foreign_currency.id, 50.0, 1, 'exchange'),
                (handed.id, foreign_currency.id, 50.0, -1, 'exchange'),
                (handed.id, foreign_currency.id, 20.0, -1, 'exchange'),
            ]))
        stock = {row['key']: row['stock'] for row in session._nm_note_stock(foreign_currency)['rows']}
        self.assertEqual(stock, {'50': 1, '20': 1, '10': 1, '5': 0})
