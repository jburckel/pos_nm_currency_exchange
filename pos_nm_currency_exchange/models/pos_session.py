# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    nm_exchange_ids = fields.One2many('pos.nm.exchange', 'session_id', string='Currency Exchanges')
    nm_exchange_count = fields.Integer(string='Exchanges', compute='_compute_nm_exchange_count')
    nm_exchange_commission = fields.Monetary(
        string='Exchange Commissions', currency_field='currency_id', compute='_compute_nm_exchange_count')

    @api.depends('nm_exchange_ids.commission')
    def _compute_nm_exchange_count(self):
        for session in self:
            session.nm_exchange_count = len(session.nm_exchange_ids)
            session.nm_exchange_commission = sum(session.nm_exchange_ids.mapped('commission'))

    def action_nm_view_exchanges(self):
        self.ensure_one()
        return {
            'name': _('Currency Exchanges'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.nm.exchange',
            'view_mode': 'list,form',
            'domain': [('session_id', '=', self.id)],
        }

    def _nm_exchange_summary(self):
        """Operations of the session for the closing popup and the report."""
        self.ensure_one()
        exchanges = self.nm_exchange_ids
        return {
            'count': len(exchanges),
            'commission': self.currency_id.round(sum(exchanges.mapped('commission'))),
            'operations': [{
                'name': exchange.name,
                'amount_in': exchange.currency_in_id.format(exchange.amount_in),
                'amount_out': exchange.currency_out_id.format(exchange.amount_out),
                'commission': exchange.commission,
                'cashier_name': exchange.cashier_name or '',
            } for exchange in exchanges.sorted('id')],
        }

    def get_closing_control_data(self):
        data = super().get_closing_control_data()
        if self.config_id.nm_exchange_enabled:
            data['nm_exchange_summary'] = self._nm_exchange_summary()
        return data
