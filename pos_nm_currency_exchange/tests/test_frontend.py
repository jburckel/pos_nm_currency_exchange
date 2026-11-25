# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_nm_multicurrencies.tests.test_frontend import TestPosMulticurrencyUi


@tagged('post_install', '-at_install')
class TestPosCurrencyExchangeUi(TestPointOfSaleHttpCommon):
    """Register tour of the exchange counter."""

    def test_pos_currency_exchange_tour(self):
        """50 EUR received at the rate 0.87 (worth 57.47), 2% commission
        (1.15): 56.32 handed back in the main currency. The receipt is
        printed again from Exchange Operations, the rates from Exchange
        Rates."""
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
        data = session.get_closing_control_data()
        self.assertEqual(data['nm_exchange_summary']['count'], 1)
        # 100 counted in the main drawer at opening less the 56.32 handed back.
        self.assertAlmostEqual(data['default_cash_details']['amount'], 43.68, places=2)

    def test_pos_currency_exchange_reverse_tour(self):
        """XPF (no decimals, 119.33 for 1 main, 5 XPF coins) besides EUR, no
        commission: 25000 XPF typed in the popup give 209.50; the customer
        then wants 10000 XPF: 83.81 received (10001 XPF rounded down to 5)."""
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
        customer is refused in the popup, the corrected one is saved on the
        customer and frozen on the operation."""
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

        exchange = session.nm_exchange_ids
        self.assertEqual(len(exchange), 1)
        self.assertEqual(exchange.partner_id, customer)
        self.assertEqual(exchange.id_document_number, 'X1234567')
        self.assertEqual(str(exchange.id_document_expiry), '2099-12-31')
        self.assertEqual(str(customer.nm_id_document_expiry), '2099-12-31')
