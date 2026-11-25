# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """20.0.2.0.0, safe to run again:

    - the reference of the operations becomes gapless: the sequence is
      noupdate, switch it to the no_gap implementation here;
    - the rate of the operations keeps 12 decimals: recompute it from the
      amounts;
    - the rate margin of the operations recorded before: computed at the
      rate of Odoo of the day of each operation.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env.ref('pos_nm_currency_exchange.seq_pos_nm_exchange', raise_if_not_found=False)
    if sequence and sequence.implementation != 'no_gap':
        sequence.implementation = 'no_gap'
    cr.execute("UPDATE pos_nm_exchange SET rate = amount_out / amount_in WHERE amount_in <> 0")
    cr.execute("SELECT id FROM pos_nm_exchange WHERE rate_margin IS NULL")
    Exchange = env['pos.nm.exchange']
    for exchange in Exchange.browse([row[0] for row in cr.fetchall()]):
        exchange.rate_margin = Exchange._nm_rate_margin(
            exchange.config_id, exchange.currency_in_id, exchange.amount_in, exchange.value_in,
            exchange.currency_out_id, exchange.amount_out, exchange.value_out, exchange.date.date())
