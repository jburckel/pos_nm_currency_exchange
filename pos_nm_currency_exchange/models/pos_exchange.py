# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import formatLang


class PosNmExchange(models.Model):
    """Currency exchange operation at the register: the customer brings
    notes in one cash currency of the point of sale and leaves with another.

    Two statement lines of the cash journal of the session, like a cash in
    and a cash out of POS Multi-Currency Cash: the notes received (in their
    currency, at the cash rate of the point of sale) and the notes handed
    back (in their currency, at the change rate). Both use the commission
    income account as counterpart: the difference between the two values is
    the commission, which lands on that account.
    """
    _name = 'pos.nm.exchange'
    _description = 'POS Currency Exchange'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default='/', copy=False)
    session_id = fields.Many2one('pos.session', string='Session', required=True, readonly=True, index=True, ondelete='restrict')
    config_id = fields.Many2one(related='session_id.config_id', store=True, index=True)
    company_id = fields.Many2one(related='session_id.company_id', store=True)
    company_currency_id = fields.Many2one(related='session_id.currency_id', string='Company Currency')
    date = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    cashier_name = fields.Char(string='Cashier', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)

    currency_in_id = fields.Many2one('res.currency', string='Received Currency', required=True, readonly=True)
    amount_in = fields.Monetary(string='Received', currency_field='currency_in_id', readonly=True,
                                help='Notes received from the customer.')
    value_in = fields.Monetary(string='Received Value', currency_field='company_currency_id', readonly=True,
                               help='Value of the notes received at the cash rate of the point of sale.')
    currency_out_id = fields.Many2one('res.currency', string='Handed Currency', required=True, readonly=True)
    amount_out = fields.Monetary(string='Handed Back', currency_field='currency_out_id', readonly=True,
                                 help='Notes handed to the customer.')
    value_out = fields.Monetary(string='Handed Value', currency_field='company_currency_id', readonly=True,
                                help='Value of the notes handed back at the change rate of the point of sale.')
    commission = fields.Monetary(string='Commission', currency_field='company_currency_id', readonly=True,
                                 help='Received value minus handed value: the commission of the counter, '
                                      'rounding of the notes handed back included.')
    rate = fields.Float(string='Rate', digits=(16, 6), readonly=True,
                        help='Units of the handed currency for one unit of the received currency, '
                             'commission included.')
    note = fields.Char(string='Note', readonly=True)
    statement_line_in_id = fields.Many2one('account.bank.statement.line', string='Received Line', readonly=True)
    statement_line_out_id = fields.Many2one('account.bank.statement.line', string='Handed Line', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pos.nm.exchange') or '/'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Quote
    # ------------------------------------------------------------------

    @api.model
    def _nm_commission_setting(self, config, currency_in, currency_out):
        """Setting carrying the commission: the foreign currency of the
        operation (the handed one when both are foreign)."""
        for currency in (currency_out, currency_in):
            if currency != config.currency_id:
                setting = config._nm_get_currency_setting(currency)
                if setting:
                    return setting
        return config.env['pos.nm.currency.setting']

    @api.model
    def _nm_rate_label(self, currency_in, currency_out, rate):
        """Rate of an operation for the popup and the receipt: "1 USD = 119.33 XPF".

        Given in the direction where it is at least 1: a rate of 0.0084 USD for
        1 XPF, rounded to the 2 decimals of the dollar, would read "$ 0.01".
        2 to 4 decimals whatever the currency (a rate of the yen or of the CFP
        franc has decimals too), without trailing zeros.
        """
        if not rate:
            return '-'
        base, quoted, value = currency_in, currency_out, rate
        if rate < 1.0:
            base, quoted, value = currency_out, currency_in, 1.0 / rate
        digits = 4 if value < 10 else 2
        while digits > 2 and round(value, digits - 1) == round(value, digits):
            digits -= 1
        number = formatLang(self.env, value, digits=digits)
        if quoted.position == 'before':
            amount = f"{quoted.symbol}\N{NO-BREAK SPACE}{number}"
        else:
            amount = f"{number}\N{NO-BREAK SPACE}{quoted.symbol}"
        return _('1 %(in)s = %(out)s', **{'in': base.name, 'out': amount})

    @api.model
    def _nm_quote(self, config, currency_in, amount_in, currency_out):
        """Amounts of an operation: value received, commission, value and
        notes handed back.

        The notes received are valued at the cash rate of the point of sale
        (what the customer pays), the notes handed back at the change rate
        (what the register hands back), the notes handed back are rounded
        down to the change rounding of their currency and the remainder
        stays in the commission.
        """
        company_currency = config.currency_id
        amount_in = currency_in.round(amount_in or 0.0)
        if currency_in == company_currency:
            value_in = amount_in
        else:
            value_in = config._nm_from_currency(amount_in, currency_in)
        setting = self._nm_commission_setting(config, currency_in, currency_out)
        commission = setting._nm_exchange_commission(value_in) if setting else 0.0
        value_out = company_currency.round(max(0.0, value_in - commission))
        if currency_out == company_currency:
            amount_out = value_out
        else:
            rate_out = config._nm_cash_rate(currency_out, change=True)
            amount_out = currency_out.round(value_out * rate_out)
            step = setting.change_rounding if setting and setting.currency_id == currency_out else 0.0
            if step:
                amount_out = currency_out.round(int(amount_out / step + 1e-9) * step)
            value_out = company_currency.round(amount_out / rate_out) if rate_out else 0.0
        commission = company_currency.round(value_in - value_out)
        return {
            'amount_in': amount_in,
            'value_in': value_in,
            'amount_out': amount_out,
            'value_out': value_out,
            'commission': commission,
            'rate': (amount_out / amount_in) if amount_in else 0.0,
            'customer_required': bool(config.nm_exchange_customer_threshold)
            and company_currency.compare_amounts(value_in, config.nm_exchange_customer_threshold) > 0,
        }

    @api.model
    def _nm_check_operation(self, config, currency_in, amount_in, currency_out):
        currencies = config._nm_exchange_currencies()
        if currency_in not in currencies or currency_out not in currencies:
            raise UserError(_("This currency is not accepted at the exchange counter of this Point of Sale."))
        if currency_in == currency_out:
            raise UserError(_("The received and handed currencies must differ."))
        if currency_in.compare_amounts(amount_in or 0.0, 0.0) <= 0:
            raise UserError(_("The received amount must be positive."))
        if not config.nm_exchange_enabled:
            raise UserError(_("The currency exchange counter is disabled on this Point of Sale."))

    @api.model
    def get_quote(self, config_id, currency_in_id, amount_in, currency_out_id):
        """Register: amounts of the operation for the popup."""
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You don't have the access rights to use the exchange counter."))
        config = self.env['pos.config'].browse(int(config_id)).exists()
        currency_in = self.env['res.currency'].browse(int(currency_in_id)).exists()
        currency_out = self.env['res.currency'].browse(int(currency_out_id)).exists()
        if not config or not currency_in or not currency_out:
            raise UserError(_("Unknown point of sale or currency."))
        self._nm_check_operation(config, currency_in, amount_in, currency_out)
        quote = self._nm_quote(config, currency_in, float(amount_in), currency_out)
        quote.update({
            'amount_in_formatted': currency_in.format(quote['amount_in']),
            'amount_out_formatted': currency_out.format(quote['amount_out']),
            'commission_formatted': config.currency_id.format(quote['commission']),
            'value_in_formatted': config.currency_id.format(quote['value_in']),
            'rate_label': self._nm_rate_label(currency_in, currency_out, quote['rate']),
        })
        return quote

    # ------------------------------------------------------------------
    # Operation
    # ------------------------------------------------------------------

    @api.model
    def create_from_ui(self, session_id, currency_in_id, amount_in, currency_out_id, partner_id=None,
                       cashier_name=None, note=None):
        """Register: record the operation and post its two statement lines.

        :return: the data of the exchange receipt
        """
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You don't have the access rights to use the exchange counter."))
        session = self.env['pos.session'].browse(int(session_id)).exists()
        if not session or session.state not in ('opened', 'closing_control'):
            raise UserError(_("The session must be open to exchange currencies."))
        config = session.config_id
        currency_in = self.env['res.currency'].browse(int(currency_in_id)).exists()
        currency_out = self.env['res.currency'].browse(int(currency_out_id)).exists()
        if not currency_in or not currency_out:
            raise UserError(_("Unknown currency."))
        self._nm_check_operation(config, currency_in, amount_in, currency_out)
        account = config.nm_exchange_income_account_id
        if not account:
            raise UserError(_(
                "Set the exchange commission account of the Point of Sale (Settings > Currency Exchange) "
                "before exchanging currencies."))
        cash_pm = session._nm_cash_payment_method()
        if not cash_pm:
            raise UserError(_("There is no cash payment method for this PoS Session"))
        quote = self._nm_quote(config, currency_in, float(amount_in), currency_out)
        if currency_out.compare_amounts(quote['amount_out'], 0.0) <= 0:
            raise UserError(_("The amount is too small for an exchange operation in %s.", currency_out.name))
        partner = self.env['res.partner'].browse(int(partner_id)).exists() if partner_id else self.env['res.partner']
        if quote['customer_required'] and not partner:
            raise UserError(_(
                "A customer must be identified for an exchange operation above %s.",
                config.currency_id.format(config.nm_exchange_customer_threshold)))
        if currency_out != config.currency_id:
            balance = config._nm_currency_balance(currency_out)
            if currency_out.compare_amounts(quote['amount_out'], balance) > 0:
                raise UserError(_(
                    "The drawer of %(currency)s holds %(balance)s: %(amount)s cannot be handed back.",
                    currency=currency_out.name, balance=currency_out.format(balance),
                    amount=currency_out.format(quote['amount_out'])))

        exchange = self.create({
            'session_id': session.id,
            'partner_id': partner.id,
            'cashier_name': cashier_name or self.env.user.name,
            'currency_in_id': currency_in.id,
            'currency_out_id': currency_out.id,
            'note': note or False,
            **{key: quote[key] for key in ('amount_in', 'value_in', 'amount_out', 'value_out', 'commission', 'rate')},
        })
        label_in = _('%(name)s: %(amount)s received', name=exchange.name, amount=currency_in.format(quote['amount_in']))
        label_out = _('%(name)s: %(amount)s handed back', name=exchange.name, amount=currency_out.format(quote['amount_out']))
        line_in = exchange._nm_post_line(
            cash_pm, session, quote['value_in'], account, label_in, partner, currency_in, quote['amount_in'])
        line_out = exchange._nm_post_line(
            cash_pm, session, -quote['value_out'], account, label_out, partner, currency_out, quote['amount_out'])
        # The cashier may create operations, not edit them: the links to the
        # lines are technical.
        exchange.sudo().write({'statement_line_in_id': line_in.id, 'statement_line_out_id': line_out.id})
        return exchange._nm_receipt_data()

    def _nm_post_line(self, cash_pm, session, amount, account, label, partner, currency, amount_currency):
        """Statement line of the cash journal in ``currency`` (a foreign
        line when it is not the currency of the point of sale), like the
        cash moves of POS Multi-Currency Cash."""
        self.ensure_one()
        config = session.config_id
        if currency == config.currency_id:
            cash_pm._create_payment_line(session, amount, account, label, partner or None)
            line = session.sudo().bank_statement_line_ids.filtered(
                lambda l: not l.foreign_currency_id and not l.nm_revaluation_currency_id).sorted('id')[-1:]
        else:
            cash_pm._create_payment_line(session, amount, account, label, partner or None, currency.id, amount_currency)
            line = session.sudo().bank_statement_line_ids.filtered(
                lambda l: l.foreign_currency_id == currency).sorted('id')[-1:]
            detail = session._nm_get_or_create_detail(currency)
            signed = amount_currency if amount > 0 else -amount_currency
            detail.cash_moves_amount = currency.round(detail.cash_moves_amount + signed)
        return line

    def _nm_receipt_data(self):
        self.ensure_one()
        company_currency = self.company_currency_id
        return {
            'id': self.id,
            'name': self.name,
            'date': fields.Datetime.context_timestamp(self, self.date).strftime('%Y-%m-%d %H:%M'),
            'cashier_name': self.cashier_name or '',
            'partner_name': self.partner_id.name or '',
            'currency_in': self.currency_in_id.name,
            'currency_out': self.currency_out_id.name,
            'label_in': _('Received (%s)', self.currency_in_id.name),
            'label_out': _('Handed back (%s)', self.currency_out_id.name),
            'amount_in': self.currency_in_id.format(self.amount_in),
            'amount_out': self.currency_out_id.format(self.amount_out),
            'value_in': company_currency.format(self.value_in),
            'commission': company_currency.format(self.commission),
            # From the amounts: the stored rate keeps 6 decimals only.
            'rate_label': self._nm_rate_label(
                self.currency_in_id, self.currency_out_id,
                (self.amount_out / self.amount_in) if self.amount_in else 0.0),
            'note': self.note or '',
        }

    def action_view_statement_lines(self):
        self.ensure_one()
        lines = self.statement_line_in_id | self.statement_line_out_id
        return {
            'name': _('Statement Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', lines.ids)],
        }
