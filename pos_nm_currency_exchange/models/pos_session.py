# -*- coding: utf-8 -*-

import math

from odoo import api, fields, models, _

from .pos_nm_note_move import _nm_note_key


class PosSession(models.Model):
    _inherit = 'pos.session'

    nm_exchange_ids = fields.One2many('pos.nm.exchange', 'session_id', string='Currency Exchanges')
    nm_exchange_count = fields.Integer(string='Exchanges', compute='_compute_nm_exchange_count')
    nm_exchange_commission = fields.Monetary(
        string='Exchange Commissions', currency_field='currency_id', compute='_compute_nm_exchange_count')

    @api.depends('nm_exchange_ids.commission', 'nm_exchange_ids.state')
    def _compute_nm_exchange_count(self):
        # Cancelled operations were reversed: they count for nothing.
        for session in self:
            exchanges = session.nm_exchange_ids.filtered(lambda e: e.state == 'done')
            session.nm_exchange_count = len(exchanges)
            session.nm_exchange_commission = sum(exchanges.mapped('commission'))

    def action_nm_view_exchanges(self):
        self.ensure_one()
        return {
            'name': _('Currency Exchanges'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.nm.exchange',
            'view_mode': 'list,form',
            'domain': [('session_id', '=', self.id)],
            'context': {'search_default_done': 1},
        }

    def _nm_exchange_summary(self):
        """Operations of the session for the closing popup and the report;
        the cancelled ones are only counted apart."""
        self.ensure_one()
        exchanges = self.nm_exchange_ids.filtered(lambda e: e.state == 'done')
        return {
            'count': len(exchanges),
            'cancelled_count': len(self.nm_exchange_ids) - len(exchanges),
            'commission': self.currency_id.round(sum(exchanges.mapped('commission'))),
            'rate_margin': self.currency_id.round(sum(exchanges.mapped('rate_margin'))),
            'operations': [{
                'name': exchange.name,
                'amount_in': exchange.currency_in_id.format(exchange.amount_in),
                'amount_out': exchange.currency_out_id.format(exchange.amount_out),
                'commission': exchange.commission,
                'cashier_name': exchange.cashier_name or '',
            } for exchange in exchanges.sorted('id')],
        }

    def _nm_expected_cash(self, currency):
        """Notes expected in the drawer of ``currency`` (the currency of the
        point of sale included), computed by the closing control: opening,
        cash payments and change of the session, cash moves and exchanges."""
        self.ensure_one()
        data = self.get_closing_control_data()
        if currency == self.currency_id:
            return data['default_cash_details'].get('amount', 0.0)
        return next((detail['amount'] for detail in data['multicurrency_details']
                     if detail['currency_id'] == currency.id), 0.0)

    def _nm_note_stock(self, currency):
        """Stock of the coins and notes of the foreign ``currency`` in the
        drawer: opening count by denomination plus the note moves of the
        session, for every coin and note of the currency (and the values
        counted or moved that are no longer one).

        :return: {'counted': the opening was counted by denomination,
            'rows': [{key, value, label, opening, moves, stock}], the largest
            value first}
        """
        self.ensure_one()
        detail = self.currency_detail_ids.filtered(lambda d: d.currency_id == currency)[:1]
        opening_details = detail.opening_details if isinstance(detail.opening_details, dict) else {}
        values, opening, moves = {}, {}, {}
        for bill in self.config_id._nm_note_bills(currency):
            values.setdefault(_nm_note_key(bill.value), bill.value)
        for raw_key, quantity in opening_details.items():
            # A malformed entry of the count is skipped, as in the report.
            try:
                value = float(raw_key)
                quantity = int(quantity or 0)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value) or value <= 0:
                continue
            key = _nm_note_key(value)
            values.setdefault(key, value)
            opening[key] = opening.get(key, 0) + quantity
        for value, quantity in self.env['pos.nm.note.move'].sudo()._read_group(
                [('session_id', '=', self.id), ('currency_id', '=', currency.id)], ['value'], ['quantity:sum']):
            key = _nm_note_key(value)
            values.setdefault(key, value)
            moves[key] = moves.get(key, 0) + quantity
        rows = []
        for key, value in sorted(values.items(), key=lambda item: item[1], reverse=True):
            rows.append({
                'key': key,
                'value': value,
                'label': currency.format(value),
                'opening': opening.get(key, 0),
                'moves': moves.get(key, 0),
                'stock': opening.get(key, 0) + moves.get(key, 0),
            })
        return {'counted': bool(opening_details), 'rows': rows}

    def get_closing_control_data(self):
        data = super().get_closing_control_data()
        # The counter may have been disabled since the operations were done.
        if self.config_id.nm_exchange_enabled or self.nm_exchange_ids:
            data['nm_exchange_summary'] = self._nm_exchange_summary()
        # Expected quantity of each coin and note of the tracked currencies.
        currencies = self.config_id._nm_note_currencies()
        for detail in data.get('multicurrency_details') or []:
            currency = currencies.filtered(lambda c: c.id == detail['currency_id'])
            if not currency:
                continue
            stock = self._nm_note_stock(currency)
            # Expected quantities only when the opening is known by
            # denomination (counted by coins/notes, or an empty drawer): an
            # opening counted by amount would expect the exchanges alone.
            if stock['counted'] or currency.is_zero(detail.get('opening') or 0.0):
                detail['nm_expected_notes'] = {row['key']: row['stock'] for row in stock['rows']}
        return data
