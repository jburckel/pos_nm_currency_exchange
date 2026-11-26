# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .test_office import ExchangeCase

# Opening count of the EUR drawer by denomination: 380 EUR.
OPENING = {'50': 4, '20': 5, '10': 5, '5': 4, '1': 10}


@tagged('post_install', '-at_install')
class TestNoteStock(ExchangeCase):
    """Note stock by denomination of the foreign drawers (EUR coins and notes
    of 50, 20, 10, 5 and 1)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bills = cls.env['pos.bill'].create([
            {'name': f'{value} EUR', 'value': value, 'currency_id': cls.fx.id} for value in (50, 20, 10, 5, 1)])
        cls.pos_config.nm_exchange_track_notes = True

    def _open_counted(self, details=None):
        return self._open(fx=380.0, main=2000.0, details={self.fx: details or OPENING})

    def _rows(self, stock):
        """Rows of the EUR coins and notes with ``stock`` ({key: qty})."""
        return [{'key': key, 'value': float(key), 'label': self.fx.format(float(key)), 'stock': stock.get(key, 0)}
                for key in ('50', '20', '10', '5', '1')]

    def _grid(self, amount):
        """Notes of ``amount`` EUR, the largest first (zeros included)."""
        grid = {}
        for value in (50, 20, 10, 5, 1):
            grid[str(value)], amount = divmod(amount, value)
        self.assertFalse(amount)
        return grid

    def _stock(self, session):
        return {row['key']: row['stock'] for row in session._nm_note_stock(self.fx)['rows']}

    # ------------------------------------------------------------------

    def test_option_off_nothing_asked(self):
        Exchange = self.env['pos.nm.exchange']
        self.pos_config.nm_exchange_track_notes = False
        self.assertFalse(self.pos_config._nm_note_currencies())
        self.assertEqual(self.pos_config._load_pos_data_read(self.pos_config, self.pos_config)[0][
            '_nm_note_currency_ids'], [])
        session = self._open_counted()
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 100.0, self.fx.id)
        self.assertIsNone(quote['notes_in'])
        self.assertIsNone(quote['notes_out'])
        receipt = Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        self.assertFalse(Exchange.browse(receipt['id']).note_move_ids)
        self.assertEqual(receipt['notes_out'], '')
        self.assertEqual(Exchange.get_note_stock(self.pos_config.id), [])
        data = session.get_closing_control_data()
        self.assertNotIn('nm_expected_notes', data['multicurrency_details'][0])

    def test_tracked_currencies(self):
        self.assertEqual(self.pos_config._nm_note_currencies(), self.fx)
        self.assertEqual(self.pos_config._load_pos_data_read(self.pos_config, self.pos_config)[0][
            '_nm_note_currency_ids'], [self.fx.id])
        # A currency without coins and notes is not tracked.
        other = self._add_cash_currency('CHF', 1.5)
        self.assertNotIn(other, self.pos_config._nm_note_currencies())
        # Coins and notes of another point of sale only do not count.
        self.env['pos.bill'].create({'name': '10 CHF', 'value': 10, 'currency_id': other.id,
                                     'pos_config_ids': [(6, 0, self.pos_config.copy().ids)]})
        self.assertNotIn(other, self.pos_config._nm_note_currencies())

    def test_proposal_largest_first_within_stock(self):
        Exchange = self.env['pos.nm.exchange']
        result = Exchange._nm_propose_notes(self.fx, 76.0, self._rows({'50': 2, '20': 2, '10': 2, '5': 2, '1': 5}))
        self.assertTrue(result['exact'])
        self.assertEqual([row['proposed'] for row in result['rows']], [1, 1, 0, 1, 1])
        self.assertFalse(result['shortfall'])
        self.assertFalse(result['error'])
        # 50 + 10 cannot be done without a 10: three notes of 20 from the stock.
        result = Exchange._nm_propose_notes(self.fx, 60.0, self._rows({'50': 1, '20': 3}))
        self.assertTrue(result['exact'])
        self.assertEqual([row['proposed'] for row in result['rows']], [0, 3, 0, 0, 0])
        self.assertFalse(result['shortfall'])

    def test_proposal_shortfall(self):
        result = self.env['pos.nm.exchange']._nm_propose_notes(self.fx, 70.0, self._rows({'20': 1}))
        self.assertTrue(result['exact'])
        self.assertEqual([row['proposed'] for row in result['rows']], [1, 1, 0, 0, 0])
        self.assertIn(f"1 x {self.fx.format(50.0)}", result['shortfall'])
        self.assertNotIn(self.fx.format(20.0), result['shortfall'])
        self.assertFalse(result['error'])

    def test_proposal_impossible(self):
        result = self.env['pos.nm.exchange']._nm_propose_notes(self.fx, 7.5, self._rows({'5': 3, '1': 9}))
        self.assertFalse(result['exact'])
        self.assertEqual([row['proposed'] for row in result['rows']], [0, 0, 0, 1, 2])
        self.assertIn('cannot be made up', result['error'])
        self.assertFalse(result['shortfall'])

    def test_quote_notes(self):
        Exchange = self.env['pos.nm.exchange']
        # No open session: nothing proposed.
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 100.0, self.fx.id)
        self.assertIsNone(quote['notes_out'])
        self._open_counted()
        quote = Exchange.get_quote(self.pos_config.id, self.main.id, 100.0, self.fx.id)
        self.assertIsNone(quote['notes_in'])  # the currency of the point of sale is not tracked
        notes_out = quote['notes_out']
        self.assertEqual(notes_out['currency_id'], self.fx.id)
        self.assertTrue(notes_out['exact'])
        self.assertEqual([row['key'] for row in notes_out['rows']], ['50', '20', '10', '5', '1'])
        self.assertEqual(set(notes_out['rows'][0]), {'key', 'value', 'label', 'stock', 'proposed'})
        self.assertEqual(notes_out['rows'][0]['stock'], 4)
        self.assertAlmostEqual(sum(row['value'] * row['proposed'] for row in notes_out['rows']), quote['amount_out'])
        self.assertEqual(notes_out['rows'][0]['proposed'], int(quote['amount_out'] // 50))
        # Notes received in EUR: their stock, nothing proposed.
        quote = Exchange.get_quote(self.pos_config.id, self.fx.id, 100.0, self.main.id)
        self.assertIsNone(quote['notes_out'])
        self.assertEqual(quote['notes_in']['currency_id'], self.fx.id)
        self.assertEqual(quote['notes_in']['rows'][3], {
            'key': '5', 'value': 5.0, 'label': self.fx.format(5.0), 'stock': 4})
        # The reverse quote gets them too.
        quote = Exchange.get_reverse_quote(self.pos_config.id, self.main.id, self.fx.id, 70.0)
        self.assertTrue(quote['notes_out']['rows'])

    def test_create_from_ui_refusals(self):
        Exchange = self.env['pos.nm.exchange']
        session = self._open_counted()
        amount_out = self._quote(self.main, 100.0, self.fx)['amount_out']
        with self.assertRaisesRegex(UserError, 'by denomination'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id)
        grid = self._grid(int(amount_out))
        with self.assertRaisesRegex(UserError, 'add up to'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id,
                                    notes_out={**grid, '1': grid['1'] + 1})
        with self.assertRaisesRegex(UserError, 'is not a coin or note'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, notes_out={**grid, '7': 0})
        with self.assertRaisesRegex(UserError, 'whole number'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, notes_out={**grid, '50': -1})
        with self.assertRaisesRegex(UserError, 'whole number'):
            Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, notes_out={**grid, '50': 0.5})
        # The notes received in EUR are required too.
        with self.assertRaisesRegex(UserError, 'notes received by denomination'):
            Exchange.create_from_ui(session.id, self.fx.id, 100.0, self.main.id)
        with self.assertRaisesRegex(UserError, 'notes received add up to'):
            Exchange.create_from_ui(session.id, self.fx.id, 100.0, self.main.id, notes_in={'50': 1})
        self.assertFalse(Exchange.search([('session_id', '=', session.id)]))
        self.assertFalse(self.env['pos.nm.note.move'].search([('session_id', '=', session.id)]))

    def test_moves_receipt_and_replay(self):
        Exchange = self.env['pos.nm.exchange']
        session = self._open_counted()
        # Received in EUR: 2 x 50 (keys of other forms are accepted).
        receipt = Exchange.with_user(self.pos_user).create_from_ui(
            session.id, self.fx.id, 100.0, self.main.id, notes_in={'50.0': 2, '20': 0}, notes_out={'5': 3})
        purchase = Exchange.browse(receipt['id'])
        self.assertEqual([(m.currency_id, m.value, m.quantity, m.origin) for m in purchase.note_move_ids],
                         [(self.fx, 50.0, 2, 'exchange')])
        self.assertEqual(receipt['notes_in'], f"2 x {self.fx.format(50.0)}")
        self.assertEqual(receipt['notes_out'], '')  # the currency of the point of sale is not tracked
        # Handed back in EUR: the notes leave the stock, even beyond it.
        amount_out = self._quote(self.main, 100.0, self.fx)['amount_out']
        grid = self._grid(int(amount_out))
        receipt = Exchange.with_user(self.pos_user).create_from_ui(
            session.id, self.main.id, 100.0, self.fx.id, notes_out=grid, uuid='nm-note-uuid')
        sale = Exchange.browse(receipt['id'])
        self.assertEqual(sorted((m.value, m.quantity) for m in sale.note_move_ids),
                         sorted((float(key), -qty) for key, qty in grid.items() if qty))
        stock = self._stock(session)
        self.assertEqual(stock['50'], OPENING['50'] + 2 - grid['50'])
        self.assertEqual(stock['1'], OPENING['1'] - grid['1'])
        self.assertIn(f"{grid['50']} x {self.fx.format(50.0)}", receipt['notes_out'])
        # The register confirms again: nothing recorded twice.
        moves = self.env['pos.nm.note.move'].search_count([])
        again = Exchange.with_user(self.pos_user).create_from_ui(
            session.id, self.main.id, 100.0, self.fx.id, notes_out=grid, uuid='nm-note-uuid')
        self.assertEqual(again['id'], sale.id)
        self.assertEqual(self.env['pos.nm.note.move'].search_count([]), moves)

    def test_cancellation_reverses_moves(self):
        Exchange = self.env['pos.nm.exchange']
        session = self._open_counted()
        receipt = Exchange.create_from_ui(session.id, self.fx.id, 100.0, self.main.id,
                                          notes_in={'50': 1, '20': 2, '10': 1})
        exchange = Exchange.browse(receipt['id'])
        self.assertEqual(self._stock(session)['20'], OPENING['20'] + 2)
        exchange.action_cancel()
        cancels = exchange.note_move_ids.filtered(lambda m: m.origin == 'cancel')
        self.assertEqual(sorted((m.value, m.quantity) for m in cancels), [(10.0, -1), (20.0, -2), (50.0, -1)])
        self.assertEqual(self._stock(session), OPENING)
        # The receipt shows the notes of the operation only.
        self.assertEqual(exchange._nm_receipt_data()['notes_in'], ', '.join([
            f"1 x {self.fx.format(50.0)}", f"2 x {self.fx.format(20.0)}", f"1 x {self.fx.format(10.0)}"]))

    def test_get_note_stock_and_closing(self):
        Exchange = self.env['pos.nm.exchange'].with_user(self.pos_user)
        self.assertEqual(Exchange.get_note_stock(self.pos_config.id), [])
        session = self._open_counted()
        Exchange.create_from_ui(session.id, self.fx.id, 100.0, self.main.id, notes_in={'50': 2})
        stock = Exchange.get_note_stock(self.pos_config.id)
        self.assertEqual(len(stock), 1)
        self.assertEqual({key: stock[0][key] for key in ('currency_id', 'name', 'counted')},
                         {'currency_id': self.fx.id, 'name': self.fx.name, 'counted': True})
        self.assertEqual(stock[0]['rows'][0], {
            'key': '50', 'value': 50.0, 'label': self.fx.format(50.0), 'opening': 4, 'moves': 2, 'stock': 6})
        self.assertEqual([row['key'] for row in stock[0]['rows']], ['50', '20', '10', '5', '1'])
        data = session.get_closing_control_data()
        detail = next(d for d in data['multicurrency_details'] if d['currency_id'] == self.fx.id)
        self.assertEqual(detail['nm_expected_notes'], {**OPENING, '50': 6})

    def test_stock_without_opening_count(self):
        session = self._open(fx=380.0, main=2000.0)
        result = session._nm_note_stock(self.fx)
        self.assertFalse(result['counted'])
        self.assertEqual([row['stock'] for row in result['rows']], [0, 0, 0, 0, 0])
        # A value counted that is no longer a coin or note still shows.
        self.bills[0].currency_id = self.main
        session.currency_detail_ids.opening_details = {'50': 1, '20': 2}
        result = session._nm_note_stock(self.fx)
        self.assertTrue(result['counted'])
        self.assertEqual([(row['key'], row['stock']) for row in result['rows']],
                         [('50', 1), ('20', 2), ('10', 0), ('5', 0), ('1', 0)])

    def test_note_stock_report(self):
        Exchange = self.env['pos.nm.exchange']
        session = self._open_counted()
        Exchange.create_from_ui(session.id, self.fx.id, 100.0, self.main.id, notes_in={'50': 1, '10': 5})
        amount_out = self._quote(self.main, 100.0, self.fx)['amount_out']
        grid = self._grid(int(amount_out))
        Exchange.create_from_ui(session.id, self.main.id, 100.0, self.fx.id, notes_out=grid)
        self.env.flush_all()
        Report = self.env['pos.nm.note.stock']
        rows = {row.value: row for row in Report.search([('session_id', '=', session.id)])}
        self.assertEqual(sorted(rows), [1.0, 5.0, 10.0, 20.0, 50.0])
        fifty = rows[50.0]
        self.assertEqual((fifty.config_id, fifty.company_id, fifty.currency_id), (
            self.pos_config, self.company, self.fx))
        self.assertEqual((fifty.opening_qty, fifty.in_qty, fifty.out_qty), (4, 1, grid['50']))
        self.assertEqual(fifty.stock_qty, 5 - grid['50'])
        self.assertEqual(rows[10.0].stock_qty, 10 - grid['10'])
        self.assertFalse(fifty.difference_qty)  # not counted at closing yet
        # Closing counted by denomination: one note of 50 less than expected.
        closing = {key: row.stock_qty for key, row in zip(('1', '5', '10', '20', '50'), (
            rows[1.0], rows[5.0], rows[10.0], rows[20.0], rows[50.0]))}
        closing['50'] -= 1
        total = sum(float(key) * qty for key, qty in closing.items())
        self._refresh_journal()
        session.set_multicurrency_counts({self.fx.id: total}, None, {self.fx.id: closing})
        self.env.flush_all()
        Report.invalidate_model()
        rows = {row.value: row for row in Report.search([('session_id', '=', session.id)])}
        self.assertEqual(rows[50.0].closing_qty, fifty.stock_qty - 1)
        self.assertEqual(rows[50.0].difference_qty, -1)
        self.assertEqual(rows[20.0].difference_qty, 0)
        self.assertEqual(rows[20.0].closing_qty, rows[20.0].stock_qty)

    def test_moves_access(self):
        Exchange = self.env['pos.nm.exchange']
        session = self._open_counted()
        receipt = Exchange.create_from_ui(session.id, self.fx.id, 100.0, self.main.id, notes_in={'50': 2})
        move = Exchange.browse(receipt['id']).note_move_ids
        self.assertEqual(move.with_user(self.pos_user).quantity, 2)
        with self.assertRaises((AccessError, UserError)):
            move.with_user(self.pos_user).write({'quantity': 5})
        with self.assertRaises(AccessError):
            move.with_user(self.pos_user).unlink()
        with self.assertRaises(AccessError):
            self.env['pos.nm.note.move'].with_user(self.pos_user).create({
                'session_id': session.id, 'currency_id': self.fx.id, 'value': 50.0, 'quantity': 1,
                'origin': 'exchange'})
        with self.assertRaises(AccessError):
            self.env['pos.nm.note.stock'].with_user(self.pos_user).search([])
        # Even with the access rights, a move is never edited nor deleted.
        with self.assertRaisesRegex(UserError, 'cannot be edited'):
            move.write({'quantity': 5})
        with self.assertRaisesRegex(UserError, 'cannot be deleted'):
            move._unlink_except_note_move()

    def test_track_notes_write_guard(self):
        with self.assertRaises(AccessError):
            self.pos_config.with_user(self.pos_user).write({'nm_exchange_track_notes': False})
        self.assertTrue(self.pos_config.nm_exchange_track_notes)
        settings = self.env['res.config.settings'].create({'pos_config_id': self.pos_config.id})
        self.assertTrue(settings.pos_nm_exchange_track_notes)

    # ------------------------------------------------------------------
    # Review fixes

    def test_proposal_impossible_is_fast(self):
        """An amount with cents and no coin below 1 is refused at once, and a
        large amount with sparse notes does not loop over the smallest one:
        both used to take tens of seconds."""
        import time
        Exchange = self.env['pos.nm.exchange']
        start = time.monotonic()
        rows = [{'key': key, 'value': float(key), 'label': key, 'stock': 0} for key in ('1000', '100', '1')]
        result = Exchange._nm_propose_notes(self.fx, 200000.5, rows)
        self.assertFalse(result['exact'])
        self.assertIn('cannot be made up', result['error'])
        rows = [{'key': key, 'value': float(key), 'label': key, 'stock': 3} for key in ('500', '1')]
        result = Exchange._nm_propose_notes(self.fx, 1000001.0, rows)
        self.assertTrue(result['exact'])
        self.assertLess(time.monotonic() - start, 2.0)

    def test_untracked_drawer_not_in_report(self):
        """A drawer counted by denomination at a point of sale that does not
        track its notes is not in the Note Stock report: its differences
        would only be the cash sales."""
        self.pos_config.nm_exchange_track_notes = False
        session = self._open_counted()
        self.env.flush_all()
        self.assertFalse(self.env['pos.nm.note.stock'].search([('session_id', '=', session.id)]))
        self.assertNotIn('nm_expected_notes', session.get_closing_control_data()['multicurrency_details'][0])

    def test_disabled_counter_tracks_nothing(self):
        self.pos_config.nm_exchange_enabled = False
        self.assertFalse(self.pos_config._nm_note_currencies())
        self.assertEqual(self.pos_config._load_pos_data_read(self.pos_config, self.pos_config)[0][
            '_nm_note_currency_ids'], [])

    def test_opening_by_amount_no_difference(self):
        """Opening counted by amount only: the stock by denomination is not
        known, so neither expected quantities at closing nor differences."""
        session = self._open(fx=380.0, main=2000.0)
        self.assertNotIn('nm_expected_notes', session.get_closing_control_data()['multicurrency_details'][0])
        self._refresh_journal()
        session.set_multicurrency_counts({self.fx.id: 380.0}, None, {self.fx.id: OPENING})
        self.env.flush_all()
        self.assertTrue(self.env['pos.nm.note.stock'].search([('session_id', '=', session.id)]))
        self.env.cr.execute(
            "SELECT count(*) FROM pos_nm_note_stock WHERE session_id = %s AND difference_qty IS NOT NULL",
            [session.id])
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_empty_drawer_at_closing_shows_shortage(self):
        """Closing counted at 0 (POS Multi-Currency Cash stores no grid for
        an empty drawer): every note of the stock is missing."""
        session = self._open_counted()
        self._refresh_journal()
        session.set_multicurrency_counts({self.fx.id: 0.0}, None, {self.fx.id: {'50': 0}})
        self.env.flush_all()
        fifty = self.env['pos.nm.note.stock'].search([('session_id', '=', session.id), ('value', '=', 50.0)])
        self.assertEqual(fifty.difference_qty, -4)

    def test_malformed_count_does_not_break_report(self):
        session = self._open_counted()
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE pos_session_currency_detail SET opening_details = %s WHERE session_id = %s",
            ['{"abc": 1, "50": "x", "20": 2}', session.id])
        self.env.flush_all()
        rows = self.env['pos.nm.note.stock'].search([('session_id', '=', session.id)])
        self.assertEqual(rows.mapped('value'), [20.0])
        session.currency_detail_ids.invalidate_recordset(['opening_details'])
        self.assertEqual(self._stock(session), {'50': 0, '20': 2, '10': 0, '5': 0, '1': 0})
