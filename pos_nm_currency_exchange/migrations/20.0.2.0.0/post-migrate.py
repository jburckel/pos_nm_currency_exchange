# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """20.0.2.0.0: the operations record their user and a state, and their
    reference becomes gapless. Safe to run again."""
    if not version:
        return
    # The operations were created by the cashier's own user.
    cr.execute("UPDATE pos_nm_exchange SET user_id = create_uid WHERE user_id IS NULL")
    cr.execute("UPDATE pos_nm_exchange SET state = 'done' WHERE state IS NULL")
    # The sequence is noupdate: switch it to the no_gap implementation here.
    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env.ref('pos_nm_currency_exchange.seq_pos_nm_exchange', raise_if_not_found=False)
    if sequence and sequence.implementation != 'no_gap':
        sequence.implementation = 'no_gap'
