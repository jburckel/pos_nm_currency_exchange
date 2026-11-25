# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """20.0.2.0.0: the reference of the operations becomes gapless. The
    sequence is noupdate: switch it to the no_gap implementation here. Safe
    to run again."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env.ref('pos_nm_currency_exchange.seq_pos_nm_exchange', raise_if_not_found=False)
    if sequence and sequence.implementation != 'no_gap':
        sequence.implementation = 'no_gap'
