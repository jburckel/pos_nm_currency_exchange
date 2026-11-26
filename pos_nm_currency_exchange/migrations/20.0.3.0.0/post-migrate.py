# -*- coding: utf-8 -*-
"""20.0.3.0.0: license frozen on the operations, hash chain of the register.

Idempotent: an operation already hashed is left as it is, the chain goes on
from the last hash of its company."""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Exchange = env['pos.nm.exchange'].with_context(active_test=False)
    for exchange in Exchange.search([('licence', '=', False)]):
        licence = exchange.config_id.nm_exchange_licence
        if licence:
            exchange.write({'licence': licence})
    for company in Exchange.search([]).company_id:
        unhashed = Exchange.search([('company_id', '=', company.id), ('register_hash', '=', False)], order='id')
        unhashed._nm_hash_register()
        for exchange in unhashed.filtered(lambda e: e.state == 'cancelled' and not e.cancel_hash):
            exchange.write({'cancel_hash': exchange._nm_compute_cancel_hash()})
        if unhashed:
            _logger.info("Exchange register of %s: %s operations hashed.", company.name, len(unhashed))
