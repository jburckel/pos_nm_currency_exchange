# -*- coding: utf-8 -*-

from odoo import fields, models

from .pos_config import EXCHANGE_INCOME_ACCOUNT_DOMAIN


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
        domain=EXCHANGE_INCOME_ACCOUNT_DOMAIN,
        readonly=False,
    )
    pos_nm_exchange_customer_threshold = fields.Monetary(
        string='Exchange Customer Required Above',
        related='pos_config_id.nm_exchange_customer_threshold',
        readonly=False,
    )
    pos_nm_exchange_customer_always = fields.Boolean(
        related='pos_config_id.nm_exchange_customer_always',
        readonly=False,
    )
    pos_nm_exchange_linked_days = fields.Integer(
        related='pos_config_id.nm_exchange_linked_days',
        readonly=False,
    )
    pos_nm_exchange_document_threshold = fields.Monetary(
        related='pos_config_id.nm_exchange_document_threshold',
        readonly=False,
    )
    pos_nm_exchange_licence = fields.Char(
        related='pos_config_id.nm_exchange_licence',
        readonly=False,
    )

    def action_nm_print_rate_board(self):
        return self.pos_config_id.action_nm_print_rate_board()
