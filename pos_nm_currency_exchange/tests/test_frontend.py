# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_nm_multicurrencies.tests.test_frontend import TestPosMulticurrencyUi


@tagged('post_install', '-at_install')
class TestPosCurrencyExchangeUi(TestPointOfSaleHttpCommon):
    """Register tour of the exchange counter."""

    def test_pos_currency_exchange_tour(self):
        """50 EUR received at the rate 0.87 (worth 57.47), 2% commission
        (1.15): 56.32 handed back in the main currency."""
        foreign_currency, cash_pm = TestPosMulticurrencyUi._setup_multicurrency(self, 60.0)
        commission_account = self.env['account.account'].create({
            'name': 'EX Tour Commissions', 'code': '999053', 'account_type': 'income_other'})
        self.main_pos_config.write({
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': commission_account.id,
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

        exchange = session.nm_exchange_ids
        self.assertEqual(len(exchange), 1)
        self.assertEqual(exchange.currency_in_id, foreign_currency)
        self.assertAlmostEqual(exchange.amount_in, 50.0, places=2)
        self.assertEqual(exchange.currency_out_id, self.main_pos_config.currency_id)
        self.assertAlmostEqual(exchange.value_in, 57.47, places=2)
        self.assertAlmostEqual(exchange.commission, 1.15, places=2)
        self.assertAlmostEqual(exchange.amount_out, 56.32, places=2)
        self.assertEqual(exchange.note, 'Tour')
        # 100 counted at opening plus the 50 received.
        self.assertAlmostEqual(self.main_pos_config._nm_currency_balance(foreign_currency), 150.0, places=2)
        data = session.get_closing_control_data()
        self.assertEqual(data['nm_exchange_summary']['count'], 1)
        self.assertAlmostEqual(data['default_cash_details']['amount'], -56.32, places=2)
