# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        """Currency exchange operations of the report: a block with every
        operation done, the totals of the commissions and rate margins per
        currency of the point of sale, and the cancelled operations apart."""
        result = super().get_sale_details(date_start, date_stop, config_ids, session_ids, **kwargs)
        all_exchanges = self._nm_report_exchanges(result['date_start'], result['date_stop'], config_ids, session_ids)
        if all_exchanges:
            result['nm_exchange'] = self._nm_exchange_block(all_exchanges)
        return result

    def _nm_report_exchanges(self, date_start, date_stop, config_ids, session_ids):
        """Operations of the reported sessions or, without sessions, the
        operations of the period (normalised by core) on the points of sale
        of the report."""
        Exchange = self.env['pos.nm.exchange']
        if session_ids:
            domain = [('session_id', 'in', session_ids)]
        else:
            domain = [('date', '>=', fields.Datetime.to_string(date_start)),
                      ('date', '<=', fields.Datetime.to_string(date_stop))]
            if config_ids:
                domain.append(('config_id', 'in', config_ids))
        return Exchange.search(domain).sorted('id')

    @api.model
    def _nm_cancelled_label(self, cancelled):
        """Line of the cancelled operations, listed by name."""
        if not cancelled:
            return ''
        if len(cancelled) == 1:
            return _('1 cancelled operation: %s', cancelled.name)
        return _('%(count)s cancelled operations: %(names)s', count=len(cancelled),
                 names=', '.join(cancelled.mapped('name')))

    def _nm_exchange_block(self, all_exchanges):
        # Cancelled operations were reversed: listed apart, out of the totals.
        exchanges = all_exchanges.filtered(lambda e: e.state == 'done')
        cancelled = all_exchanges - exchanges
        # Commissions and rate margins are in the currency of the point of
        # sale of each operation: never added across currencies.
        currencies = exchanges.company_currency_id.sorted('name')
        totals = []
        for currency in currencies:
            group = exchanges.filtered(lambda e: e.company_currency_id == currency)
            if len(currencies) > 1:
                if len(group) == 1:
                    count_label = _('1 operation in %(currency)s', currency=currency.name)
                else:
                    count_label = _('%(count)s operations in %(currency)s', count=len(group), currency=currency.name)
            else:
                count_label = _('1 operation') if len(group) == 1 else _('%s operations', len(group))
            commission = currency.round(sum(group.mapped('commission')))
            rate_margin = currency.round(sum(group.mapped('rate_margin')))
            totals.append({
                'currency': currency.name,
                'count': len(group),
                'count_label': count_label,
                'commission': commission,
                'commission_formatted': currency.format(commission),
                'rate_margin': rate_margin,
                'rate_margin_formatted': currency.format(rate_margin),
            })
        return {
            'count': len(exchanges),
            'totals': totals,
            'cancelled_count': len(cancelled),
            'cancelled_label': self._nm_cancelled_label(cancelled),
            'operations': [{
                'name': exchange.name,
                'session': exchange.session_id.name,
                'amount_in': exchange.currency_in_id.format(exchange.amount_in),
                'amount_out': exchange.currency_out_id.format(exchange.amount_out),
                'commission': exchange.company_currency_id.format(exchange.commission),
                'rate_margin': exchange.company_currency_id.format(exchange.rate_margin),
            } for exchange in exchanges],
        }
