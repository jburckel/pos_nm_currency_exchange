# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user, tagged

from .test_office import ExchangeCase

# Opening count of the EUR drawer of the first counter by denomination: 380 EUR.
OPENING = {'50': 4, '20': 5, '10': 5, '5': 4, '1': 10}


@tagged('post_install', '-at_install')
class TestNoteTransfer(ExchangeCase):
    """Transfers of notes between the counters of an exchange office: the
    point of sale of the tests and a second counter with its own cash
    journal and EUR drawer (1 main = 2 EUR at the rate of Odoo)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.transit_account = cls.env['account.account'].create({
            'name': 'NM Notes in Transit', 'code': '999061', 'account_type': 'asset_current'})
        cls.office = cls.env['pos.nm.exchange.office'].create({
            'name': 'NM Office', 'transit_account_id': cls.transit_account.id})
        cls.pos_config.nm_exchange_office_id = cls.office
        journal = cls.env['account.journal'].create({
            'name': 'NM Cash 2', 'code': 'NMC2', 'type': 'cash', 'company_id': cls.company.id})
        cls.cash_pm2 = cls.env['pos.payment.method'].create({
            'name': 'NM Cash 2', 'journal_id': journal.id, 'type': 'cash', 'currency_ids': [(4, cls.fx.id)]})
        cls.config2 = cls.pos_config.copy({'name': 'NM Counter 2'})
        cls.config2.write({
            'nm_exchange_enabled': True,
            'nm_exchange_income_account_id': cls.commission_account.id,
            'nm_exchange_office_id': cls.office.id,
            'payment_method_ids': [(6, 0, cls.cash_pm2.ids)],
        })
        cls.bills = cls.env['pos.bill'].create([
            {'name': f'{value} EUR', 'value': value, 'currency_id': cls.fx.id} for value in (50, 20, 10, 5, 1)])
        cls.Transfer = cls.env['pos.nm.exchange.transfer']

    def _open2(self, fx=0.0, main=0.0, details=None):
        """Open a session of the second counter."""
        self.config2.open_ui()
        session = self.config2.current_session_id
        session.set_multicurrency_counts({str(self.fx.id): fx}, None,
                                         {str(self.fx.id): details} if details else {})
        session.set_opening_control(main, '')
        return session

    def _open_both(self, details=None):
        session1 = self._open(fx=380.0, main=1000.0, details={self.fx: details} if details else None)
        session2 = self._open2(fx=0.0, main=0.0)
        return session1, session2

    def _transit_balance(self):
        lines = self.env['account.move.line'].search([('account_id', '=', self.transit_account.id)])
        return self.company.currency_id.round(sum(lines.mapped('balance')))

    def _send(self, session, amount, currency=None, **kwargs):
        return self.Transfer.send_from_ui(session.id, self.config2.id, (currency or self.main).id, amount, **kwargs)

    def _stock(self, session):
        return {row['key']: row['stock'] for row in session._nm_note_stock(self.fx)['rows'] if row['stock']}

    # ------------------------------------------------------------------

    def test_send_receive_main_currency(self):
        session1, session2 = self._open_both()
        cash1 = session1._nm_expected_cash(self.main)
        cash2 = session2._nm_expected_cash(self.main)
        data = self._send(session1, 300.0, note='For the afternoon')
        transfer = self.Transfer.browse(data['id'])
        self.assertEqual(data['state'], 'sent')
        self.assertTrue(data['name'].startswith('TRF/'))
        self.assertEqual(data['config_from'], self.pos_config.name)
        self.assertEqual(data['config_to'], 'NM Counter 2')
        self.assertEqual(data['currency'], self.main.name)
        self.assertEqual(data['amount_formatted'], self.main.format(300.0))
        self.assertEqual(data['notes_label'], '')
        self.assertEqual(transfer.value, 300.0)
        self.assertEqual(transfer.session_from_id, session1)
        self.assertEqual(transfer.sent_user_id, self.env.user)
        line = transfer.statement_line_from_id
        self.assertEqual(line.amount, -300.0)
        self.assertEqual(line.pos_session_id, session1)
        self.assertEqual(line.payment_ref, f'{transfer.name}: notes sent to NM Counter 2')
        self.assertEqual(self._transit_balance(), 300.0)
        self.assertEqual(session1._nm_expected_cash(self.main), cash1 - 300.0)
        # The cash moves of the closing popup list the line.
        moves = session1.get_closing_control_data()['default_cash_details']['moves']
        self.assertIn(line.payment_ref, [move['name'] for move in moves])

        incoming = self.Transfer.get_incoming_transfers(self.config2.id)
        self.assertEqual([t['id'] for t in incoming], [transfer.id])
        self.assertEqual(incoming[0]['config_from'], self.pos_config.name)
        self.assertEqual(incoming[0]['note'], 'For the afternoon')
        self.assertEqual(self.Transfer.get_incoming_transfers(self.pos_config.id), [])

        data = self.Transfer.receive_from_ui(transfer.id, session2.id)
        self.assertEqual(data['state'], 'received')
        self.assertEqual(transfer.state, 'received')
        self.assertEqual(transfer.session_to_id, session2)
        line = transfer.statement_line_to_id
        self.assertEqual(line.amount, 300.0)
        self.assertEqual(line.pos_session_id, session2)
        self.assertEqual(line.payment_ref, f'{transfer.name}: notes received from {self.pos_config.name}')
        self.assertEqual(self._transit_balance(), 0.0)
        self.assertEqual(session2._nm_expected_cash(self.main), cash2 + 300.0)
        self.assertEqual(self.Transfer.get_incoming_transfers(self.config2.id), [])
        # Received again (lost response): nothing recorded twice.
        self.assertEqual(self.Transfer.receive_from_ui(transfer.id, session2.id)['id'], transfer.id)
        self.assertEqual(len(session2.bank_statement_line_ids.filtered(
            lambda line: transfer.name in (line.payment_ref or ''))), 1)

    def test_send_receive_foreign_currency(self):
        session1, session2 = self._open_both()
        fx1 = session1._nm_expected_cash(self.fx)
        detail1 = session1._nm_get_or_create_detail(self.fx).cash_moves_amount
        data = self._send(session1, 200.0, currency=self.fx)
        transfer = self.Transfer.browse(data['id'])
        # 200 EUR at the rate of Odoo of the day: 100.
        self.assertEqual(transfer.value, 100.0)
        line = transfer.statement_line_from_id
        self.assertEqual(line.amount, -100.0)
        self.assertEqual(line.foreign_currency_id, self.fx)
        self.assertEqual(line.amount_currency, -200.0)
        self.assertEqual(session1._nm_get_or_create_detail(self.fx).cash_moves_amount, detail1 - 200.0)
        self.assertEqual(session1._nm_expected_cash(self.fx), fx1 - 200.0)
        self.assertEqual(self._transit_balance(), 100.0)
        detail = next(d for d in session1.get_closing_control_data()['multicurrency_details']
                      if d['currency_id'] == self.fx.id)
        self.assertIn(line.payment_ref, [move['name'] for move in detail['moves']])

        # The rate of the day changes: the value received is the value sent.
        self.env['res.currency.rate'].create({'currency_id': self.fx.id, 'rate': 4.0, 'company_id': self.company.id})
        self.Transfer.receive_from_ui(transfer.id, session2.id)
        line = transfer.statement_line_to_id
        self.assertEqual(line.amount, 100.0)
        self.assertEqual(line.amount_currency, 200.0)
        self.assertEqual(session2._nm_get_or_create_detail(self.fx).cash_moves_amount, 200.0)
        self.assertEqual(session2._nm_expected_cash(self.fx), 200.0)
        self.assertEqual(self._transit_balance(), 0.0)

    def test_note_moves_tracked_at_both_counters(self):
        self.pos_config.nm_exchange_track_notes = True
        self.config2.nm_exchange_track_notes = True
        session1, session2 = self._open_both(details=OPENING)
        targets = self.Transfer.get_transfer_targets(self.pos_config.id)
        self.assertEqual(targets['targets'], [{'id': self.config2.id, 'name': 'NM Counter 2', 'session_open': True}])
        currencies = {c['id']: c for c in targets['currencies']}
        self.assertEqual(set(currencies), {self.main.id, self.fx.id})
        self.assertFalse(currencies[self.main.id]['tracked'])
        self.assertEqual(currencies[self.main.id]['rows'], [])
        self.assertTrue(currencies[self.fx.id]['tracked'])
        self.assertEqual([(r['key'], r['stock']) for r in currencies[self.fx.id]['rows']],
                         [('50', 4), ('20', 5), ('10', 5), ('5', 4), ('1', 10)])
        self.assertEqual(set(currencies[self.fx.id]['rows'][0]), {'key', 'value', 'label', 'stock'})

        data = self._send(session1, 120.0, currency=self.fx, notes={'50': 2, '10': 2, '20': 0})
        self.assertEqual(data['notes_label'], f"2 x {self.fx.format(50)}, 2 x {self.fx.format(10)}")
        transfer = self.Transfer.browse(data['id'])
        self.assertEqual(transfer.notes, {'50': 2, '10': 2})
        self.assertEqual(self._stock(session1), {'50': 2, '20': 5, '10': 3, '5': 4, '1': 10})
        self.assertEqual(set(transfer.note_move_ids.mapped('origin')), {'transfer'})
        self.assertEqual(self.Transfer.get_incoming_transfers(self.config2.id)[0]['notes_label'], data['notes_label'])
        self.Transfer.receive_from_ui(transfer.id, session2.id)
        self.assertEqual(self._stock(session2), {'50': 2, '10': 2})
        self.assertEqual(len(transfer.note_move_ids), 4)

    def test_note_moves_tracked_at_one_counter(self):
        # Tracked at the sending counter only: no moves at the receiving one.
        self.pos_config.nm_exchange_track_notes = True
        session1, session2 = self._open_both(details=OPENING)
        transfer = self.Transfer.browse(self._send(session1, 50.0, currency=self.fx, notes={'50': 1})['id'])
        self.Transfer.receive_from_ui(transfer.id, session2.id)
        self.assertEqual(transfer.note_move_ids.session_id, session1)
        self.assertFalse(self._stock(session2))
        # Tracked at the receiving counter only: counted at receiving.
        self.pos_config.nm_exchange_track_notes = False
        self.config2.nm_exchange_track_notes = True
        transfer = self.Transfer.browse(self._send(session1, 70.0, currency=self.fx)['id'])
        self.assertFalse(transfer.notes)
        self.assertFalse(transfer.note_move_ids)
        incoming = self.Transfer.get_incoming_transfers(self.config2.id)[0]
        self.assertTrue(incoming['needs_notes'])
        self.assertEqual(incoming['currency_id'], self.fx.id)
        self.assertEqual(incoming['amount'], 70.0)
        self.assertEqual([row['key'] for row in incoming['rows']], ['50', '20', '10', '5', '1'])
        for notes, message in (
            (None, 'Enter the notes received'),
            ({'50': 1}, 'notes received add up to'),
            ({'30': 2, '10': 1}, 'not a coin or note'),
        ):
            with self.subTest(notes=notes), self.assertRaisesRegex(UserError, message):
                self.Transfer.receive_from_ui(transfer.id, session2.id, notes=notes)
        self.assertEqual(transfer.state, 'sent')
        data = self.Transfer.receive_from_ui(transfer.id, session2.id, notes={'20': 3, '10': 1, '50': 0})
        self.assertEqual(data['notes_label'], f"3 x {self.fx.format(20)}, 1 x {self.fx.format(10)}")
        self.assertEqual(transfer.notes, {'20': 3, '10': 1})
        self.assertEqual(transfer.note_move_ids.session_id, session2)
        self.assertEqual(self._stock(session2), {'20': 3, '10': 1})
        # From the back office, a breakdown of the amount, the largest first.
        transfer = self.Transfer.browse(self._send(session1, 75.0, currency=self.fx)['id'])
        self.assertFalse(self.Transfer.get_incoming_transfers(self.config2.id)[0]['rows'][0]['stock'] < 0)
        transfer.action_receive()
        self.assertEqual(transfer.notes, {'50': 1, '20': 1, '5': 1})
        self.assertEqual(self._stock(session2), {'50': 1, '20': 4, '10': 1, '5': 1})
        # Counted at both counters: the notes sent, not counted again.
        self.pos_config.nm_exchange_track_notes = True
        transfer = self.Transfer.browse(self._send(session1, 10.0, currency=self.fx, notes={'10': 1})['id'])
        self.assertFalse(self.Transfer.get_incoming_transfers(self.config2.id)[0]['needs_notes'])
        self.Transfer.receive_from_ui(transfer.id, session2.id, notes={'5': 2})
        self.assertEqual(transfer.notes, {'10': 1})
        self.assertEqual(self._stock(session2)['10'], 2)
        # The currency of the point of sale is never tracked.
        transfer = self.Transfer.browse(self._send(session1, 10.0)['id'])
        self.assertFalse(self.Transfer.get_incoming_transfers(self.config2.id)[0]['needs_notes'])
        self.Transfer.receive_from_ui(transfer.id, session2.id)
        self.assertFalse(transfer.note_move_ids)

    def test_note_grid_refusals(self):
        self.pos_config.nm_exchange_track_notes = True
        session1, _session2 = self._open_both(details=OPENING)
        for notes, message in (
            (None, 'Enter the notes sent'),
            ({'50': 1}, 'add up to'),
            ({'30': 2, '50': 0}, 'not a coin or note'),
            ({'50': 1.5, '10': 1.5}, 'whole number'),
            ({'50': -1, '20': 5, '10': 0}, 'whole number'),
        ):
            with self.subTest(notes=notes), self.assertRaisesRegex(UserError, message):
                self._send(session1, 60.0, currency=self.fx, notes=notes)
        self.assertFalse(self.Transfer.search([]))
        # A shortfall of the stock is not refused: 6 x 20 for 5 in the drawer.
        transfer = self.Transfer.browse(self._send(session1, 120.0, currency=self.fx, notes={'20': 6})['id'])
        self.assertEqual(transfer.state, 'sent')
        self.assertEqual(self._stock(session1)['20'], -1)

    def test_drawer_check(self):
        session1, _session2 = self._open_both()
        with self.assertRaisesRegex(UserError, 'cannot be sent'):
            self._send(session1, 381.0, currency=self.fx)
        with self.assertRaisesRegex(UserError, 'cannot be sent'):
            self._send(session1, 1000.01)
        with self.assertRaisesRegex(UserError, 'positive'):
            self._send(session1, 0.0)
        self.assertFalse(self.Transfer.search([]))
        self._send(session1, 380.0, currency=self.fx)

    def test_counters_refused(self):
        # A currency of the sending counter only.
        chf = self._add_cash_currency('CHF', 1.5)
        session1, session2 = self._open_both()
        # The same counter.
        with self.assertRaisesRegex(ValidationError, 'counter that sends them'):
            self.Transfer.send_from_ui(session1.id, self.pos_config.id, self.main.id, 10.0)
        # A counter of no office, or of another office.
        other = self.pos_config.copy({'name': 'NM Elsewhere', 'nm_exchange_office_id': False})
        with self.assertRaisesRegex(ValidationError, 'not a counter of the exchange office'):
            self.Transfer.send_from_ui(session1.id, other.id, self.main.id, 10.0)
        other.nm_exchange_office_id = self.env['pos.nm.exchange.office'].create({'name': 'NM Office 2'})
        with self.assertRaisesRegex(ValidationError, 'not a counter of the exchange office'):
            self.Transfer.send_from_ui(session1.id, other.id, self.main.id, 10.0)
        # A currency the receiving counter does not take in cash.
        with self.assertRaisesRegex(ValidationError, 'does not take CHF'):
            self._send(session1, 10.0, currency=chf)
        # The sending counter outside any office.
        self.config2.nm_exchange_office_id = False
        self.pos_config.nm_exchange_office_id = False
        with self.assertRaisesRegex(UserError, 'does not belong to an exchange office'):
            self._send(session1, 10.0)
        self.pos_config.nm_exchange_office_id = self.office
        self.config2.nm_exchange_office_id = self.office
        # The receiving counter without open session.
        transfer = self.Transfer.browse(self._send(session1, 10.0)['id'])
        with self.assertRaisesRegex(UserError, 'not sent to this counter'):
            self.Transfer.receive_from_ui(transfer.id, session1.id)
        self._refresh_journal()
        session2.set_multicurrency_counts({self.fx.id: 0.0})
        self.assertTrue(session2.close_session_from_ui({self.cash_pm2.id: 0.0})['status'])
        with self.assertRaisesRegex(UserError, 'must be open'):
            self.Transfer.receive_from_ui(transfer.id, session2.id)
        with self.assertRaisesRegex(UserError, 'has no open session'):
            transfer.action_receive()
        # The sending session closed.
        self._close(session1, main=session1._nm_expected_cash(self.main), fx=380.0)
        with self.assertRaisesRegex(UserError, 'must be open'):
            self._send(session1, 10.0)
        # A disabled counter.
        session1 = self._open(fx=380.0, main=990.0)
        self.pos_config.nm_exchange_enabled = False
        with self.assertRaisesRegex(UserError, 'disabled'):
            self._send(session1, 10.0)

    def test_value_rounding_to_zero_refused(self):
        # 100000 units for 1 company currency: 1 unit is worth 0.00001.
        tiny = self._add_cash_currency('IDR', 100000.0)
        self.cash_pm2.currency_ids = [(4, tiny.id)]
        session1 = self._open(fx=380.0, main=1000.0, counts={tiny: 5000.0})
        session2 = self._open2()
        with self.assertRaisesRegex(UserError, 'too small to be transferred'):
            self._send(session1, 100.0, currency=tiny)
        self.assertFalse(self.Transfer.search([]))
        self.assertEqual(self._transit_balance(), 0.0)
        # The smallest amount worth a cent goes through.
        transfer = self.Transfer.browse(self._send(session1, 1000.0, currency=tiny)['id'])
        self.assertEqual(transfer.value, 0.01)
        self.Transfer.receive_from_ui(transfer.id, session2.id)
        self.assertEqual(session2._nm_get_or_create_detail(tiny).cash_moves_amount, 1000.0)
        # A foreign line worth 0 adds its amount to the drawer, as core
        # signs it (copysign): a cash in, not a cash out.
        detail = session2._nm_get_or_create_detail(tiny)
        line = self.env['pos.nm.exchange']._nm_post_line(
            self.cash_pm2, session2, 0.0, self.transit_account, 'NM zero', self.env.user.partner_id, tiny, 4.0)
        self.assertEqual(line.amount_currency, 4.0)
        self.assertEqual(detail.cash_moves_amount, 1004.0)

    def test_system_fields_refused(self):
        session1, session2 = self._open_both()
        manager = new_test_user(self.env, login='nm_transfer_manager', groups='point_of_sale.group_pos_manager',
                                company_id=self.company.id)
        Transfer = self.Transfer.with_user(manager)
        vals = {'office_id': self.office.id, 'config_from_id': self.pos_config.id, 'config_to_id': self.config2.id,
                'currency_id': self.main.id, 'amount': 50.0}
        # The defaults of the form are accepted.
        draft = Transfer.create({**vals, 'name': '/', 'state': 'draft', 'note_move_ids': []})
        self.assertEqual(draft.state, 'draft')
        for field, value in (
            ('state', 'sent'), ('value', 1000.0), ('session_from_id', session1.id), ('name', 'TRF/FAKE'),
            ('notes', {'50': 1}), ('sent_user_id', manager.id), ('uuid', 'nm-fake'),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(UserError, 'set when the notes are sent'):
                    Transfer.create({**vals, field: value})
                with self.assertRaisesRegex(UserError, 'set when the notes are sent'):
                    draft.write({field: value})
        self.assertEqual((draft.state, draft.value, draft.name), ('draft', 0.0, '/'))
        # Forged behind the ORM: never received nor cancelled with a cash in.
        draft.sudo().write({'state': 'sent', 'session_from_id': session1.id, 'value': 1000.0})
        with self.assertRaisesRegex(UserError, 'not in transit'):
            draft.action_receive()
        with self.assertRaisesRegex(UserError, 'not in transit'):
            draft.action_cancel()
        self.assertFalse(session2.bank_statement_line_ids.filtered(lambda line: line.amount == 1000.0))
        # The manager still edits a draft and sends it.
        draft = Transfer.create(vals)
        draft.amount = 40.0
        draft.action_send()
        self.assertEqual((draft.state, draft.value), ('sent', 40.0))
        draft.note = 'Checked'

    def test_uuid_replay(self):
        session1, _session2 = self._open_both()
        data = self._send(session1, 100.0, uuid='nm-transfer-1')
        again = self._send(session1, 100.0, uuid='nm-transfer-1')
        self.assertEqual(again['id'], data['id'])
        self.assertEqual(again['name'], data['name'])
        self.assertEqual(self.Transfer.search_count([]), 1)
        self.assertEqual(self._transit_balance(), 100.0)
        with self.assertRaisesRegex(UserError, 'already recorded'):
            self._send(session1, 90.0, uuid='nm-transfer-1')

    def test_gapless_reference_on_sending(self):
        session1, _session2 = self._open_both()
        draft = self.Transfer.create({
            'office_id': self.office.id, 'config_from_id': self.pos_config.id, 'config_to_id': self.config2.id,
            'currency_id': self.main.id, 'amount': 50.0})
        self.assertEqual(draft.name, '/')
        self.assertEqual(draft.company_id, self.company)
        first = self.Transfer.browse(self._send(session1, 10.0)['id'])
        # Refused before the number: nothing in the drawer.
        with self.assertRaises(UserError):
            self._send(session1, 5000.0)
        draft.action_send()
        prefix, number = first.name.rsplit('/', 1)
        self.assertEqual(draft.name, f"{prefix}/{int(number) + 1:05d}")
        self.assertEqual(draft.state, 'sent')
        self.assertEqual(draft.session_from_id, session1)

    def test_cancel(self):
        self.pos_config.nm_exchange_track_notes = True
        session1, session2 = self._open_both(details=OPENING)
        fx1 = session1._nm_expected_cash(self.fx)
        # A draft is cancelled without any line.
        draft = self.Transfer.create({
            'office_id': self.office.id, 'config_from_id': self.pos_config.id, 'config_to_id': self.config2.id,
            'currency_id': self.main.id, 'amount': 50.0})
        draft.action_cancel()
        self.assertEqual(draft.state, 'cancelled')
        self.assertFalse(draft.statement_line_cancel_id)
        with self.assertRaisesRegex(UserError, 'already cancelled'):
            draft.action_cancel()
        # In transit: the notes go back to the drawer of the sending session.
        transfer = self.Transfer.browse(self._send(session1, 70.0, currency=self.fx, notes={'50': 1, '20': 1})['id'])
        self.assertEqual(session1._nm_expected_cash(self.fx), fx1 - 70.0)
        transfer.action_cancel()
        self.assertEqual(transfer.state, 'cancelled')
        line = transfer.statement_line_cancel_id
        self.assertEqual(line.pos_session_id, session1)
        self.assertEqual(line.amount, 35.0)
        self.assertEqual(line.amount_currency, 70.0)
        self.assertEqual(session1._nm_expected_cash(self.fx), fx1)
        self.assertEqual(self._transit_balance(), 0.0)
        self.assertEqual(self._stock(session1), OPENING)
        self.assertEqual(sorted(transfer.note_move_ids.mapped('origin')), ['cancel', 'cancel', 'transfer', 'transfer'])
        self.assertEqual(self.Transfer.get_incoming_transfers(self.config2.id), [])
        with self.assertRaisesRegex(UserError, 'not in transit'):
            self.Transfer.receive_from_ui(transfer.id, session2.id)
        # Received: refused.
        transfer = self.Transfer.browse(self._send(session1, 10.0)['id'])
        self.Transfer.receive_from_ui(transfer.id, session2.id)
        with self.assertRaisesRegex(UserError, 'was received'):
            transfer.action_cancel()
        # Sending session closed: refused.
        transfer = self.Transfer.browse(self._send(session1, 10.0)['id'])
        self._close(session1, main=session1._nm_expected_cash(self.main), fx=session1._nm_expected_cash(self.fx))
        with self.assertRaisesRegex(UserError, 'closed session'):
            transfer.action_cancel()
        # It can still be received.
        self.Transfer.receive_from_ui(transfer.id, session2.id)
        self.assertEqual(transfer.state, 'received')

    def test_cancel_by_the_cashier(self):
        session1, _session2 = self._open_both()
        cashier = self.pos_user
        other = new_test_user(self.env, login='nm_transfer_cashier_2', groups='point_of_sale.group_pos_user',
                              company_id=self.company.id)
        data = self.Transfer.with_user(cashier).send_from_ui(session1.id, self.config2.id, self.main.id, 20.0)
        transfer = self.Transfer.browse(data['id'])
        self.assertEqual(transfer.sent_user_id, cashier)
        with self.assertRaises(AccessError):
            transfer.with_user(other).action_cancel()
        transfer.with_user(cashier).action_cancel()
        self.assertEqual(transfer.state, 'cancelled')
        self.assertEqual(transfer.cancel_user_id, cashier)
        draft = self.Transfer.create({
            'office_id': self.office.id, 'config_from_id': self.pos_config.id, 'config_to_id': self.config2.id,
            'currency_id': self.main.id, 'amount': 50.0})
        with self.assertRaises(AccessError):
            draft.with_user(cashier).action_cancel()

    def test_statement_lines_not_deletable(self):
        session1, session2 = self._open_both()
        transfer = self.Transfer.browse(self._send(session1, 10.0)['id'])
        with self.assertRaisesRegex(UserError, 'note transfer'):
            transfer.statement_line_from_id.unlink()
        with self.assertRaisesRegex(UserError, 'note transfer'):
            session1.delete_cash_in_out(transfer.statement_line_from_id.id, self.env.user.partner_id.id)
        self.Transfer.receive_from_ui(transfer.id, session2.id)
        with self.assertRaisesRegex(UserError, 'note transfer'):
            transfer.statement_line_to_id.unlink()

    def test_immutable_once_sent(self):
        session1, _session2 = self._open_both()
        draft = self.Transfer.create({
            'office_id': self.office.id, 'config_from_id': self.pos_config.id, 'config_to_id': self.config2.id,
            'currency_id': self.main.id, 'amount': 50.0})
        draft.amount = 40.0
        draft.unlink()
        transfer = self.Transfer.browse(self._send(session1, 10.0)['id'])
        transfer.note = 'Checked'
        with self.assertRaisesRegex(UserError, 'cannot be edited'):
            transfer.amount = 20.0
        with self.assertRaisesRegex(UserError, 'Only a draft'):
            transfer.unlink()
        with self.assertRaisesRegex(UserError, 'already sent'):
            transfer.action_send()

    def test_access(self):
        session1, session2 = self._open_both()
        cashier = self.pos_user
        vals = {'office_id': self.office.id, 'config_from_id': self.pos_config.id, 'config_to_id': self.config2.id,
                'currency_id': self.main.id, 'amount': 50.0}
        with self.assertRaises(AccessError):
            self.Transfer.with_user(cashier).create(vals)
        transfer = self.Transfer.browse(self._send(session1, 10.0)['id'])
        transfer.with_user(cashier).check_access('read')
        with self.assertRaises(AccessError):
            transfer.with_user(cashier).write({'note': 'x'})
        with self.assertRaises(AccessError):
            transfer.with_user(cashier).action_receive()
        draft = self.Transfer.create(vals)
        with self.assertRaises(AccessError):
            draft.with_user(cashier).action_send()
        # The RPCs need a POS user.
        outsider = new_test_user(self.env, login='nm_transfer_outsider', groups='base.group_user',
                                 company_id=self.company.id)
        Outsider = self.Transfer.with_user(outsider)
        for call in (
            lambda: Outsider.get_transfer_targets(self.pos_config.id),
            lambda: Outsider.send_from_ui(session1.id, self.config2.id, self.main.id, 10.0),
            lambda: Outsider.get_incoming_transfers(self.config2.id),
            lambda: Outsider.receive_from_ui(transfer.id, session2.id),
        ):
            with self.assertRaises(AccessError):
                call()
        # The cashier sends and receives from the register.
        data = self.Transfer.with_user(cashier).send_from_ui(session1.id, self.config2.id, self.main.id, 10.0)
        self.assertEqual(self.Transfer.with_user(cashier).receive_from_ui(data['id'], session2.id)['state'],
                         'received')
        self.assertEqual(self.Transfer.browse(data['id']).received_user_id, cashier)

    def test_transit_account_required(self):
        session1, _session2 = self._open_both()
        self.office.transit_account_id = False
        with self.assertRaisesRegex(UserError, 'Notes in Transit Account'):
            self._send(session1, 10.0)
        with self.assertRaises(ValidationError):
            self.office.transit_account_id = self.commission_account

    def test_register_flag(self):
        def flag(config):
            return config._load_pos_data_read(config, config)[0]['_nm_transfer_enabled']
        self.assertTrue(flag(self.pos_config))
        self.config2.nm_exchange_office_id = False
        self.assertFalse(flag(self.pos_config))
        self.config2.nm_exchange_office_id = self.office
        # The other counter is disabled: it cannot receive at its register.
        session1, _session2 = self._open_both()
        self.config2.nm_exchange_enabled = False
        self.assertFalse(flag(self.pos_config))
        self.assertEqual(self.Transfer.get_transfer_targets(self.pos_config.id)['targets'], [])
        with self.assertRaisesRegex(UserError, 'disabled on NM Counter 2'):
            self._send(session1, 10.0)
        self.config2.nm_exchange_enabled = True
        self.pos_config.nm_exchange_enabled = False
        self.assertFalse(flag(self.pos_config))

    def test_office_drawers(self):
        session1, session2 = self._open_both()
        Exchange = self.env['pos.nm.exchange']
        receipt = Exchange.create_from_ui(session1.id, self.main.id, 100.0, self.fx.id)
        exchange = Exchange.browse(receipt['id'])
        self._send(session1, 100.0, currency=self.fx)
        self._send(session1, 50.0)
        received = self.Transfer.browse(self._send(session1, 30.0)['id'])
        self.Transfer.receive_from_ui(received.id, session2.id)
        drawers = self.office._nm_drawers()
        counters = {counter['config']: counter for counter in drawers['counters']}
        self.assertEqual(set(counters), {self.pos_config.name, 'NM Counter 2'})
        first = counters[self.pos_config.name]
        self.assertEqual(first['session'], session1.name)
        cash = {row['currency']: row['amount'] for row in first['cash']}
        self.assertEqual(cash[self.main.name], session1._nm_expected_cash(self.main))
        self.assertEqual(cash[self.fx.name], session1._nm_expected_cash(self.fx))
        self.assertEqual(first['operation_count'], 1)
        self.assertEqual(first['commission'], exchange.commission)
        second = {row['currency']: row['amount'] for row in counters['NM Counter 2']['cash']}
        self.assertEqual(second[self.main.name], 30.0)
        self.assertEqual(counters['NM Counter 2']['operation_count'], 0)
        transit = {row['currency']: row for row in drawers['in_transit']}
        self.assertEqual(transit[self.fx.name]['amount'], 100.0)
        self.assertEqual(transit[self.fx.name]['value'], 50.0)
        self.assertEqual(transit[self.main.name]['amount'], 50.0)
        self.assertEqual(drawers['in_transit_value'], 100.0)
        self.assertEqual(drawers['in_transit_value'], self._transit_balance())
        self.assertEqual(drawers['operation_count'], 1)
        self.assertIn(session1.name, self.office.drawers_html)
        self.assertIn('o_nm_office_drawers_transit', self.office.drawers_html)
        self.assertEqual(self.office.transfer_count, 3)
        # A counter whose session is closed is left out.
        self._refresh_journal()
        session2.set_multicurrency_counts({self.fx.id: 0.0})
        self.assertTrue(session2.close_session_from_ui({self.cash_pm2.id: 30.0})['status'])
        self.office.invalidate_recordset(['drawers_html'])
        self.assertEqual([c['config'] for c in self.office._nm_drawers()['counters']], [self.pos_config.name])

    def test_back_office_send_proposes_notes(self):
        self.pos_config.nm_exchange_track_notes = True
        session1, session2 = self._open_both(details=OPENING)
        draft = self.Transfer.create({
            'office_id': self.office.id, 'config_from_id': self.pos_config.id, 'config_to_id': self.config2.id,
            'currency_id': self.fx.id, 'amount': 120.0})
        draft.action_send()
        self.assertEqual(draft.notes, {'50': 2, '20': 1})
        self.assertEqual(self._stock(session1), {'50': 2, '20': 4, '10': 5, '5': 4, '1': 10})
        draft.action_receive()
        self.assertEqual(draft.session_to_id, session2)
        # Notes the stock cannot make up (100 EUR cashed in without
        # denominations): sent from the register.
        session1.nm_try_cash_in_out_currency('in', 100.0, 'NM', self.env.user.partner_id.id, self.fx.id)
        draft = self.Transfer.create({
            'office_id': self.office.id, 'config_from_id': self.pos_config.id, 'config_to_id': self.config2.id,
            'currency_id': self.fx.id, 'amount': 300.0})
        with self.assertRaisesRegex(UserError, 'Enter the notes sent'):
            draft.action_send()
