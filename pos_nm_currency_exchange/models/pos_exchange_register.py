# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ReportExchangeRegister(models.AbstractModel):
    """Exchange register: every operation of a period on the chosen points
    of sale, in the order of the references (gapless), the cancelled ones
    included, with the totals per currency."""
    _name = 'report.pos_nm_currency_exchange.report_exchange_register'
    _description = 'Exchange Register'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        Exchange = self.env['pos.nm.exchange']
        date_start = fields.Datetime.to_datetime(data.get('date_start'))
        date_stop = fields.Datetime.to_datetime(data.get('date_stop'))
        configs = self.env['pos.config'].browse(data.get('config_ids') or [])
        domain = [('date', '>=', date_start), ('date', '<=', date_stop)]
        if configs:
            domain.append(('config_id', 'in', configs.ids))
        exchanges = Exchange.search(domain, order='name, id')
        return {
            'date_start': Exchange._nm_local_datetime(date_start),
            'date_stop': Exchange._nm_local_datetime(date_stop),
            'config_names': ', '.join(configs.mapped('name')) or _('All'),
            'operations': [self._nm_operation_row(exchange) for exchange in exchanges],
            'totals': self._nm_totals(exchanges.filtered(lambda e: e.state == 'done')),
            'cancelled_count': len(exchanges.filtered(lambda e: e.state == 'cancelled')),
        }

    @api.model
    def _nm_operation_row(self, exchange):
        company_currency = exchange.company_currency_id
        document = exchange._fields['id_document_type']._description_selection(self.env)
        return {
            'name': exchange.name,
            'date': exchange._nm_local_datetime(exchange.date),
            'config': exchange.config_id.name,
            'cashier': exchange.cashier_name or '',
            'operation_type': dict(exchange._fields['operation_type']._description_selection(self.env)).get(
                exchange.operation_type, ''),
            'amount_in': exchange.currency_in_id.format(exchange.amount_in),
            'amount_out': exchange.currency_out_id.format(exchange.amount_out),
            'rate': exchange.rate_label,
            'commission': company_currency.format(exchange.commission),
            'rate_margin': company_currency.format(exchange.rate_margin),
            'customer': exchange.customer_name or '',
            'document_type': dict(document).get(exchange.id_document_type, ''),
            'document_number': exchange.id_document_number or '',
            'document_country': exchange.id_document_country_id.name or '',
            'document_expiry': fields.Date.to_string(exchange.id_document_expiry) or '',
            'cancelled': exchange.state == 'cancelled',
            'state': dict(exchange._fields['state']._description_selection(self.env))[exchange.state],
        }

    @api.model
    def _nm_totals(self, exchanges):
        """Per currency: the operations, the notes received and handed back
        and the balance of its drawer; for the currency of a point of sale,
        the commissions and rate margins of its operations."""
        totals = []
        currencies = exchanges.currency_in_id | exchanges.currency_out_id | exchanges.company_currency_id
        for currency in currencies.sorted('name'):
            received = exchanges.filtered(lambda e: e.currency_in_id == currency)
            handed = exchanges.filtered(lambda e: e.currency_out_id == currency)
            company_group = exchanges.filtered(lambda e: e.company_currency_id == currency)
            amount_in = currency.round(sum(received.mapped('amount_in')))
            amount_out = currency.round(sum(handed.mapped('amount_out')))
            totals.append({
                'currency': currency.name,
                'count': len(received | handed),
                'amount_in': currency.format(amount_in),
                'amount_out': currency.format(amount_out),
                'balance': currency.format(amount_in - amount_out),
                'commission': currency.format(sum(company_group.mapped('commission'))) if company_group else '',
                'rate_margin': currency.format(sum(company_group.mapped('rate_margin'))) if company_group else '',
            })
        return totals
