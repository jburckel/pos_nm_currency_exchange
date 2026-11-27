# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import HttpCase, new_test_user, tagged

from .test_exchange import TestPosCurrencyExchange


class ExchangeCase(TestPosCurrencyExchange):
    """Setup of the exchange tests without their test methods (inherited
    test methods are disabled: they run in TestPosCurrencyExchange)."""


for _name in dir(TestPosCurrencyExchange):
    if _name.startswith('test_'):
        setattr(ExchangeCase, _name, None)


@tagged('post_install', '-at_install')
class TestExchangeOffice(ExchangeCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.office = cls.env['pos.nm.exchange.office'].create({
            'name': 'NM Office',
            'licence': 'LIC-OFFICE',
        })

    def _cash_method(self):
        """Cash payment method of a second counter, with the EUR drawer."""
        journal = self.env['account.journal'].create({
            'name': 'NM Cash 2', 'code': 'NMC2', 'type': 'cash', 'company_id': self.company.id})
        return self.env['pos.payment.method'].create({
            'name': 'NM Cash 2', 'journal_id': journal.id, 'type': 'cash', 'currency_ids': [(4, self.fx.id)]})

    def _second_counter(self):
        config = self.pos_config.copy({'name': 'NM Counter 2'})
        config.write({
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': self.commission_account.id,
            'nm_exchange_office_id': self.office.id,
            'payment_method_ids': [(6, 0, self._cash_method().ids)],
        })
        return config

    def test_office_rules_replace_counter_rules(self):
        Exchange = self.env['pos.nm.exchange']
        self.pos_config.write({'nm_exchange_document_threshold': 0.0, 'nm_exchange_licence': 'LIC-POS'})
        self.assertEqual(self.pos_config._nm_rules()['licence'], 'LIC-POS')
        self.office.write({'customer_threshold': 50.0, 'document_threshold': 0.0})
        self.pos_config.nm_exchange_office_id = self.office
        rules = self.pos_config._nm_rules()
        self.assertEqual(rules['licence'], 'LIC-OFFICE')
        self.assertEqual(rules['customer_threshold'], 50.0)
        identification = Exchange._nm_identification(self.pos_config, 100.0, self.env['res.partner'])
        self.assertTrue(identification['customer_required'])
        session = self._open(fx=1000.0, main=1000.0)
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, self.partner_id)
        exchange = Exchange.browse(receipt['id'])
        self.assertEqual(receipt['licence'], 'LIC-OFFICE')
        self.assertEqual(exchange.office_id, self.office)
        self.assertEqual(exchange.licence, 'LIC-OFFICE')
        # The license is frozen on the operation.
        self.office.licence = 'LIC-NEW'
        self.assertEqual(Exchange.get_receipt(exchange.id)['licence'], 'LIC-OFFICE')

    def test_office_constraints(self):
        with self.assertRaises(ValidationError):
            self.office.review_threshold = -1
        with self.assertRaises(ValidationError):
            self.office.board_refresh = 5
        other = self.pos_config.copy({'name': 'NM Elsewhere'})
        with self.assertRaises(ValidationError):
            self.office.reference_config_id = other

    def test_counter_settings_reserved_to_managers(self):
        with self.assertRaises(AccessError):
            self.pos_config.with_user(self.pos_user).write({'nm_exchange_office_id': self.office.id})

    def test_apply_rates_to_the_counters(self):
        self.pos_config.nm_exchange_office_id = self.office
        counter = self._second_counter()
        self.office.reference_config_id = self.pos_config
        differences = self.office._nm_rate_differences()
        self.assertEqual(len(differences), 1)
        self.assertFalse(differences[0]['field'])  # EUR not set on the second counter
        self.assertIs(self.office.action_nm_apply_rates(), True)
        setting = counter._nm_get_currency_setting(self.fx)
        self.assertEqual(setting.margin_percent, 10.0)
        self.assertEqual(setting.exchange_sell_margin_percent, 10.0)
        self.assertEqual(setting.exchange_commission_percent, 2.0)
        self.assertEqual(setting.exchange_commission_min, 3.0)
        self.assertFalse(self.office._nm_rate_differences())
        # A change of the reference counter is a difference until applied,
        # logged in the chatter of the setting of the counter.
        self.setting.exchange_commission_percent = 2.5
        self.assertEqual(len(self.office._nm_rate_differences()), 1)
        before = len(setting.message_ids)
        self.office.action_nm_apply_rates()
        self.assertEqual(setting.exchange_commission_percent, 2.5)
        self.assertEqual(len(setting.message_ids), before + 1)
        # Same quote at both counters.
        Exchange = self.env['pos.nm.exchange']
        self.assertEqual(
            Exchange._nm_quote(self.pos_config, self.main, 100.0, self.fx),
            Exchange._nm_quote(counter, self.main, 100.0, self.fx))
        with self.assertRaises(UserError):
            self.office.with_user(self.pos_user).action_nm_apply_rates()

    def test_office_rate_board(self):
        self.pos_config.nm_exchange_office_id = self.office
        board = self.office._nm_rate_board()
        self.assertEqual(board['config_name'], 'NM Office')
        self.assertEqual(board['licence'], 'LIC-OFFICE')
        self.assertEqual([row['currency'] for row in board['rows']], [self.fx.name])
        self.assertEqual(self.pos_config._nm_rate_board()['licence'], 'LIC-OFFICE')


@tagged('post_install', '-at_install')
class TestExchangeCompliance(ExchangeCase):

    def test_origin_of_funds_threshold(self):
        Exchange = self.env['pos.nm.exchange']
        self.pos_config.nm_exchange_origin_threshold = 150.0
        session = self._open(fx=2000.0, main=2000.0)
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 200.0, self.fx.id, self.partner_id)
        self.assertTrue(quote['origin_required'])
        self.assertTrue(quote['customer_required'])
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 200.0, self.fx.id)
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 200.0, self.fx.id, self.partner_id)
        with self.assertRaises(UserError):
            Exchange.create_from_ui(session.id, self.main.id, 200.0, self.fx.id, self.partner_id,
                                    declaration={'funds_origin': 'other'})
        receipt = Exchange.create_from_ui(
            session.id, self.main.id, 200.0, self.fx.id, self.partner_id,
            declaration={'funds_origin': 'savings', 'purpose': 'travel', 'pep': False, 'funds_origin_note': ' '})
        exchange = Exchange.browse(receipt['id'])
        self.assertEqual(exchange.funds_origin, 'savings')
        self.assertEqual(exchange.purpose, 'travel')
        self.assertFalse(exchange.funds_origin_note)
        self.assertEqual(exchange.compliance_state, 'none')
        # Below the threshold, nothing is asked.
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        self.assertFalse(Exchange.browse(receipt['id']).funds_origin)

    def test_review_threshold_and_pep(self):
        Exchange = self.env['pos.nm.exchange']
        officer = new_test_user(self.env, login='nm_officer', groups='point_of_sale.group_pos_manager',
                                company_id=self.company.id)
        office = self.env['pos.nm.exchange.office'].create({
            'name': 'NM Office', 'review_threshold': 150.0, 'compliance_user_id': officer.id})
        self.pos_config.nm_exchange_office_id = office
        session = self._open(fx=2000.0, main=2000.0)
        small = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        self.assertEqual(small.compliance_state, 'none')
        big = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 200.0, self.fx.id)['id'])
        self.assertEqual(big.compliance_state, 'to_review')
        self.assertIn('review threshold', big.review_reason)
        self.assertEqual(big.activity_ids.user_id, officer)
        pep = Exchange.browse(Exchange.create_from_ui(
            session.id, self.main.id, 50.0, self.fx.id, self.partner_id, declaration={'pep': True})['id'])
        self.assertEqual(pep.compliance_state, 'to_review')
        self.assertTrue(pep.pep)
        # The manager reviews; the cashier cannot.
        with self.assertRaises(AccessError):
            big.with_user(self.pos_user).write({'compliance_state': 'reviewed'})
        big.write({'compliance_state': 'reviewed', 'compliance_note': 'Known customer'})
        self.assertEqual(big.compliance_state, 'reviewed')
        with self.assertRaises(UserError):
            big.write({'amount_in': 1.0})

    def test_register_hash_chain(self):
        Exchange = self.env['pos.nm.exchange']
        session = self._open(fx=2000.0, main=2000.0)
        first = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        second = Exchange.browse(Exchange.create_from_ui(session.id, self.fx.id, 220.0, self.main.id)['id'])
        self.assertTrue(first.register_hash)
        self.assertEqual(second.register_previous_hash, first.register_hash)
        self.assertEqual(len(second.register_hash), 64)
        second.action_cancel()
        self.assertTrue(second.cancel_hash)
        result = Exchange._nm_check_register_integrity(self.company)
        self.assertFalse(result['broken'], result)
        self.assertEqual(result['last'], second.name)
        # Altered in the database behind the ORM: detected.
        self.env.cr.execute("UPDATE pos_nm_exchange SET amount_out = amount_out + 1 WHERE id = %s", [first.id])
        first.invalidate_recordset(['amount_out'])
        result = Exchange._nm_check_register_integrity(self.company)
        self.assertEqual(result['broken'], first.name)
        self.env.cr.execute("UPDATE pos_nm_exchange SET amount_out = amount_out - 1 WHERE id = %s", [first.id])
        first.invalidate_recordset(['amount_out'])
        self.assertFalse(Exchange._nm_check_register_integrity(self.company)['broken'])
        # Even with sudo, a hashed operation cannot be changed by the ORM.
        with self.assertRaises(UserError):
            first.sudo().write({'amount_in': 1.0})

    def test_register_closing(self):
        Exchange = self.env['pos.nm.exchange']
        Closing = self.env['pos.nm.exchange.register.closing']
        session = self._open(fx=2000.0, main=2000.0)
        exchange = Exchange.browse(Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)['id'])
        start = fields.Datetime.now() - timedelta(hours=1)
        stop = fields.Datetime.now() + timedelta(seconds=1)
        with self.assertRaises(UserError):  # the period is not over
            Closing._nm_close(self.company, self.env['pos.nm.exchange.office'], start, stop + timedelta(days=1))
        with self.assertRaises(UserError):  # its session is open
            Closing._nm_close(self.company, self.env['pos.nm.exchange.office'], start, fields.Datetime.now())
        stop = fields.Datetime.now()
        self.env.cr.execute("UPDATE pos_session SET state = 'closed' WHERE id = %s", [session.id])
        session.invalidate_recordset(['state'])
        closing = Closing._nm_close(self.company, self.env['pos.nm.exchange.office'], start, stop)
        self.assertEqual(closing.operation_count, 1)
        self.assertEqual(closing.last_operation, exchange.name)
        self.assertEqual(closing.last_hash, exchange.register_hash)
        self.assertEqual(closing.commission, exchange.commission)
        self.assertTrue(closing.attachment_id)
        with self.assertRaises(UserError):
            Closing._nm_close(self.company, self.env['pos.nm.exchange.office'], start, stop)
        with self.assertRaises(UserError):
            closing.unlink()
        with self.assertRaises(UserError):
            closing.with_user(self.env.ref('base.user_admin')).write({'operation_count': 2})
        self.assertEqual(Closing._nm_closed_until(exchange), closing)


@tagged('post_install', '-at_install')
class TestExchangeRateBoardPage(HttpCase):

    def test_board_routes(self):
        config = self.env['pos.config'].search([], limit=1)
        config.nm_exchange_enabled = True
        response = self.url_open(f'/pos_nm_exchange/board/{config.id}?access_token=wrong')
        self.assertEqual(response.status_code, 404)
        response = self.url_open(f'/pos_nm_exchange/board/{config.id}?access_token={config.access_token}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('nm-board', response.text)
        response = self.url_open(f'/pos_nm_exchange/board/{config.id}/data?access_token={config.access_token}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('rows', response.json())
        config.nm_exchange_enabled = False
        response = self.url_open(f'/pos_nm_exchange/board/{config.id}?access_token={config.access_token}')
        self.assertEqual(response.status_code, 404)
        config.nm_exchange_enabled = True
        office = self.env['pos.nm.exchange.office'].create({'name': 'Board Office', 'licence': 'L-1'})
        response = self.url_open(f'/pos_nm_exchange/office_board/{office.id}?access_token={office.board_token}')
        self.assertEqual(response.status_code, 404)  # no counter
        config.nm_exchange_office_id = office
        response = self.url_open(f'/pos_nm_exchange/office_board/{office.id}?access_token={office.board_token}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Board Office', response.text)
        self.assertIn('L-1', response.text)
        response = self.url_open(f'/pos_nm_exchange/office_board/{office.id}?access_token={config.access_token}')
        self.assertEqual(response.status_code, 404)
        config.nm_exchange_board_on_display = True
        self.assertIn('/pos_nm_exchange/board/', config._get_customer_display_data()['nm_rate_board_url'])

    def test_board_language(self):
        """The board speaks the language of the company, or the one given
        with ?lang= when it is installed; its refresh keeps that language."""
        self.env['res.lang']._activate_lang('fr_FR')
        self.env['ir.module.module']._load_module_terms(['pos_nm_currency_exchange'], ['fr_FR'], overwrite=True)
        config = self.env['pos.config'].search([], limit=1)
        config.nm_exchange_enabled = True
        url = f'/pos_nm_exchange/board/{config.id}?access_token={config.access_token}'
        response = self.url_open(url + '&lang=fr_FR')
        self.assertIn('lang="fr-FR"', response.text)
        self.assertIn('Nous achetons', response.text)
        self.assertIn('lang=fr_FR', response.text)  # the refresh keeps the language
        response = self.url_open(url + '&lang=xx_XX')  # not installed: the company's
        self.assertIn('We buy', response.text)
        config.company_id.partner_id.lang = 'fr_FR'
        self.assertIn('Nous achetons', self.url_open(url).text)
