# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import SQL

NOTE_MOVE_ORIGINS = [
    ('exchange', 'Exchange'),
    ('cancel', 'Cancellation'),
]


def _nm_note_key(value):
    """Key of a coin or note of ``value`` in the counts by denomination:
    "50", "0.5", "5000", as the register and POS Multi-Currency Cash write
    it (``String(bill.value)``)."""
    return ('%.4f' % value).rstrip('0').rstrip('.')


class PosNmNoteMove(models.Model):
    """Coins and notes of a foreign drawer received or handed back by
    denomination, at a point of sale tracking its notes: the stock of a
    denomination during a session is its opening count plus these moves.

    Written by the operations (with sudo), never edited nor deleted.
    """
    _name = 'pos.nm.note.move'
    _description = 'Note Move'
    _order = 'date desc, id desc'

    session_id = fields.Many2one('pos.session', string='Session', required=True, readonly=True, index=True,
                                 ondelete='restrict')
    config_id = fields.Many2one(related='session_id.config_id', store=True, index=True)
    company_id = fields.Many2one(related='session_id.company_id', store=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True)
    value = fields.Float(string='Denomination', digits=(16, 4), required=True, readonly=True, aggregator=None)
    quantity = fields.Integer(
        string='Quantity', readonly=True,
        help='Coins or notes put in the drawer (positive) or taken out of it (negative).')
    origin = fields.Selection(NOTE_MOVE_ORIGINS, string='Origin', required=True, readonly=True)
    exchange_id = fields.Many2one('pos.nm.exchange', string='Exchange Operation', readonly=True, index=True,
                                  ondelete='restrict')
    date = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)

    def write(self, vals):
        if not self.env.su:
            raise UserError(_("A note move cannot be edited: it is written by its operation."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_note_move(self):
        if not self.env.su:
            raise UserError(_("A note move cannot be deleted: cancel its operation instead."))


class PosNmNoteStock(models.Model):
    """Note stock of the foreign drawers per session and denomination:
    opening count, notes received and handed back by the operations, stock,
    closing count and difference with the stock when the closing was
    counted by denomination."""
    _name = 'pos.nm.note.stock'
    _description = 'Note Stock'
    _auto = False
    _order = 'session_id desc, currency_id, value desc'
    _rec_name = 'value'

    session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    config_id = fields.Many2one('pos.config', string='Point of Sale', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    value = fields.Float(string='Denomination', digits=(16, 4), readonly=True, aggregator=None)
    opening_qty = fields.Integer(string='Opening', readonly=True, help='Quantity counted at opening.')
    in_qty = fields.Integer(string='In', readonly=True, help='Quantity put in the drawer by the operations.')
    out_qty = fields.Integer(string='Out', readonly=True,
                             help='Quantity taken out of the drawer by the operations.')
    stock_qty = fields.Integer(string='Stock', readonly=True, help='Opening + In - Out.')
    closing_qty = fields.Integer(string='Closing', readonly=True, help='Quantity counted at closing.')
    difference_qty = fields.Integer(
        string='Difference', readonly=True,
        help='Closing - Stock, when the closing was counted by denomination.')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""
            CREATE OR REPLACE VIEW %s AS (
                WITH counts AS (
                    SELECT detail.session_id, detail.currency_id, ROUND(item.key::numeric, 4) AS value,
                           item.value::numeric AS opening_qty, 0 AS in_qty, 0 AS out_qty, 0 AS closing_qty
                      FROM pos_session_currency_detail detail,
                           jsonb_each_text(CASE WHEN jsonb_typeof(detail.opening_details) = 'object'
                                                THEN detail.opening_details ELSE '{}'::jsonb END) item
                     WHERE item.key ~ '^\s*[0-9]+(\.[0-9]+)?\s*$' AND item.value ~ '^\s*-?[0-9]+\s*$'
                    UNION ALL
                    SELECT detail.session_id, detail.currency_id, ROUND(item.key::numeric, 4),
                           0, 0, 0, item.value::numeric
                      FROM pos_session_currency_detail detail,
                           jsonb_each_text(CASE WHEN jsonb_typeof(detail.closing_details) = 'object'
                                                THEN detail.closing_details ELSE '{}'::jsonb END) item
                     WHERE item.key ~ '^\s*[0-9]+(\.[0-9]+)?\s*$' AND item.value ~ '^\s*-?[0-9]+\s*$'
                    UNION ALL
                    SELECT move.session_id, move.currency_id, ROUND(move.value::numeric, 4),
                           0, GREATEST(move.quantity, 0), GREATEST(-move.quantity, 0), 0
                      FROM pos_nm_note_move move
                ), stock AS (
                    SELECT session_id, currency_id, value,
                           SUM(opening_qty)::integer AS opening_qty,
                           SUM(in_qty)::integer AS in_qty,
                           SUM(out_qty)::integer AS out_qty,
                           SUM(closing_qty)::integer AS closing_qty
                      FROM counts
                  GROUP BY session_id, currency_id, value
                )
                SELECT ROW_NUMBER() OVER (ORDER BY stock.session_id, stock.currency_id, stock.value) AS id,
                       stock.session_id,
                       session.config_id,
                       config.company_id,
                       stock.currency_id,
                       stock.value,
                       stock.opening_qty,
                       stock.in_qty,
                       stock.out_qty,
                       stock.opening_qty + stock.in_qty - stock.out_qty AS stock_qty,
                       stock.closing_qty,
                       -- Only when both counts are known by denomination: a closing
                       -- counted by coins/notes (or an empty drawer, stored without
                       -- grid by POS Multi-Currency Cash), against an opening counted
                       -- by coins/notes or empty.
                       CASE WHEN (jsonb_typeof(detail.closing_details) = 'object'
                                  OR (detail.closing_counted AND COALESCE(detail.closing_amount, 0) = 0))
                             AND (jsonb_typeof(detail.opening_details) = 'object'
                                  OR COALESCE(detail.opening_amount, 0) = 0)
                            THEN stock.closing_qty - (stock.opening_qty + stock.in_qty - stock.out_qty)
                       END AS difference_qty
                  FROM stock
                  JOIN pos_session session ON session.id = stock.session_id
                  JOIN pos_config config ON config.id = session.config_id
             LEFT JOIN pos_session_currency_detail detail
                    ON detail.session_id = stock.session_id AND detail.currency_id = stock.currency_id
                 -- The drawers whose notes are tracked: the option is ticked, or
                 -- the session has note moves (option switched off since).
                 WHERE config.nm_exchange_track_notes
                    OR EXISTS (SELECT 1 FROM pos_nm_note_move m
                                WHERE m.session_id = stock.session_id AND m.currency_id = stock.currency_id)
            )
        """, SQL.identifier(self._table)))
