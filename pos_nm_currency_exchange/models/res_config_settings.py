# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_nm_exchange_enabled = fields.Boolean(
        string='Currency Exchange',
        related='pos_config_id.nm_exchange_enabled',
        readonly=False,
    )
    pos_nm_exchange_income_account_id = fields.Many2one(
        string='Exchange Commission Account',
        related='pos_config_id.nm_exchange_income_account_id',
        readonly=False,
    )
    pos_nm_exchange_customer_threshold = fields.Monetary(
        string='Exchange Customer Required Above',
        related='pos_config_id.nm_exchange_customer_threshold',
        readonly=False,
    )
