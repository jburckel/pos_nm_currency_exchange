# -*- coding: utf-8 -*-

import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """20.0.2.0.0, safe to run again:

    - the reference of the operations becomes gapless: the sequence is
      noupdate, switch it to the no_gap implementation here;
    - the rate of the operations keeps 12 decimals: recompute it from the
      amounts;
    - the rate margin of the operations recorded before: computed at the
      rate of Odoo of the day of each operation;
    - the operations keep the name of their customer, and the value
      compared to the identification thresholds (no linked operations
      before);
    - the operations one of whose statement lines was deleted (20.0.1.x
      allowed it) still count their commission and cannot be cancelled:
      they are logged and a message on each names the missing line, for
      the manager to correct the drawer with a cash move.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env.ref('pos_nm_currency_exchange.seq_pos_nm_exchange', raise_if_not_found=False)
    if sequence and sequence.implementation != 'no_gap':
        sequence.implementation = 'no_gap'
    cr.execute("UPDATE pos_nm_exchange SET rate = amount_out / amount_in WHERE amount_in <> 0")
    cr.execute("""
        UPDATE pos_nm_exchange exchange SET customer_name = partner.name
          FROM res_partner partner
         WHERE partner.id = exchange.partner_id AND exchange.customer_name IS NULL
    """)
    cr.execute("UPDATE pos_nm_exchange SET linked_value = value_in WHERE linked_value IS NULL")
    cr.execute("SELECT id FROM pos_nm_exchange WHERE rate_margin IS NULL")
    Exchange = env['pos.nm.exchange']
    for exchange in Exchange.browse([row[0] for row in cr.fetchall()]):
        exchange.rate_margin = Exchange._nm_rate_margin(
            exchange.config_id, exchange.currency_in_id, exchange.amount_in, exchange.value_in,
            exchange.currency_out_id, exchange.amount_out, exchange.value_out, exchange.date.date())
    cr.execute("""
        SELECT id FROM pos_nm_exchange
         WHERE state = 'done' AND (statement_line_in_id IS NULL OR statement_line_out_id IS NULL)
    """)
    broken = Exchange.browse([row[0] for row in cr.fetchall()])
    if broken:
        _logger.warning("Exchange operations with a deleted statement line: %s", ', '.join(broken.mapped('name')))
    for exchange in broken:
        # Already reported by an earlier run (the migration runs as en_US).
        if env['mail.message'].search_count([
            ('model', '=', exchange._name), ('res_id', '=', exchange.id),
            ('body', 'ilike', 'was deleted before the upgrade to 20.0.2.0.0'),
        ]):
            continue
        legs = []
        if not exchange.statement_line_in_id:
            legs.append(env._("received (%s)", exchange.currency_in_id.format(exchange.amount_in)))
        if not exchange.statement_line_out_id:
            legs.append(env._("handed back (%s)", exchange.currency_out_id.format(exchange.amount_out)))
        exchange.message_post(body=env._(
            "The statement line of the notes %(legs)s of this operation was deleted before the upgrade to "
            "20.0.2.0.0: the drawer and the commission account are off by that line, and the operation cannot "
            "be cancelled. Correct the drawer with a cash move.", legs=', '.join(legs)))
