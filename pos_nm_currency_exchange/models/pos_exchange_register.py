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
        office = self.env['pos.nm.exchange.office'].browse(data.get('office_id') or [])
        company = self.env['res.company'].browse(data.get('company_id') or [])
        closing = self.env['pos.nm.exchange.register.closing'].sudo().browse(data.get('closing_id') or [])
        domain = [('date', '>=', date_start), ('date', '<=', date_stop)]
        if office:
            domain.append(('office_id', '=', office.id))
        elif configs:
            domain.append(('config_id', 'in', configs.ids))
        if company:
            domain.append(('company_id', '=', company.id))
        exchanges = Exchange.search(domain, order='name, id')
        return {
            'office_name': office.name or '',
            'office_address': office.partner_id._display_address(without_name=True).replace('\n', ', ')
            if office.partner_id else '',
            'office_licence': office.licence or '',
            'closing': {
                'name': closing.name,
                'user': closing.user_id.name,
                'last_operation': closing.last_operation or '',
                'last_hash': closing.last_hash or '',
                'integrity': closing.integrity or '',
            } if closing else False,
            'date_start': Exchange._nm_local_datetime(date_start),
            'date_stop': Exchange._nm_local_datetime(date_stop),
            'config_names': ', '.join((office.config_ids if office else configs).mapped('name')) or _('All'),
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
            'document_no_expiry': exchange.id_document_no_expiry,
            'customer_address': exchange.customer_address or '',
            'nationality': exchange.id_nationality_id.name or '',
            'birthdate': fields.Date.to_string(exchange.id_birthdate) or '',
            'funds_origin': dict(exchange._fields['funds_origin']._description_selection(self.env)).get(
                exchange.funds_origin, ''),
            'funds_origin_note': exchange.funds_origin_note or '',
            'purpose': dict(exchange._fields['purpose']._description_selection(self.env)).get(exchange.purpose, ''),
            'pep': exchange.pep,
            'compliance': dict(exchange._fields['compliance_state']._description_selection(self.env)).get(
                exchange.compliance_state, '') if exchange.compliance_state != 'none' else '',
            'register_hash': (exchange.register_hash or '')[:12],
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
