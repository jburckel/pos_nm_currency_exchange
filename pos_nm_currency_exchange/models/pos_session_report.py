# -*- coding: utf-8 -*-

from odoo import models, _


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        """Currency exchange operations of the reported sessions: a block
        with every operation done, the total of the commissions and the
        number of cancelled operations."""
        result = super().get_sale_details(date_start, date_stop, config_ids, session_ids, **kwargs)
        payments = result.get('payments') or []
        session_ids_in_report = {p['session'] for p in payments if p.get('session')}
        if session_ids:
            session_ids_in_report |= set(session_ids)
        sessions = self.env['pos.session'].browse(sorted(session_ids_in_report)).exists()
        all_exchanges = sessions.nm_exchange_ids.sorted('id') if sessions else self.env['pos.nm.exchange']
        # Cancelled operations were reversed: counted apart, out of the totals.
        exchanges = all_exchanges.filtered(lambda e: e.state == 'done')
        if all_exchanges:
            currency = sessions[0].currency_id
            cancelled_count = len(all_exchanges) - len(exchanges)
            result['nm_exchange'] = {
                'count': len(exchanges),
                'count_label': _('%s operations', len(exchanges)),
                'cancelled_count': cancelled_count,
                'cancelled_label': _('%s cancelled operations', cancelled_count) if cancelled_count else '',
                'commission': currency.round(sum(exchanges.mapped('commission'))),
                'operations': [{
                    'name': exchange.name,
                    'session': exchange.session_id.name,
                    'amount_in': exchange.currency_in_id.format(exchange.amount_in),
                    'amount_out': exchange.currency_out_id.format(exchange.amount_out),
                    'commission': exchange.commission,
                } for exchange in exchanges],
            }
        return result
