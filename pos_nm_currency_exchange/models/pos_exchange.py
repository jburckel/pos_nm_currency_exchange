# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
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
    _check_company_auto = True

    name = fields.Char(string='Reference', required=True, readonly=True, default='/', copy=False)
    state = fields.Selection(
        [('done', 'Done'), ('cancelled', 'Cancelled')], string='Status', required=True, readonly=True,
        default='done', index=True,
        help='Done: the notes were exchanged. Cancelled: the operation was reversed by two opposite '
             'statement lines; it no longer counts in the commissions.')
    session_id = fields.Many2one('pos.session', string='Session', required=True, readonly=True, index=True,
                                 ondelete='restrict', check_company=True)
    config_id = fields.Many2one(related='session_id.config_id', store=True, index=True)
    company_id = fields.Many2one(related='session_id.company_id', store=True, index=True)
    company_currency_id = fields.Many2one(related='session_id.currency_id', string='Company Currency')
    date = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True, default=lambda self: self.env.user,
                              help='User logged in to Odoo who recorded the operation.')
    cashier_name = fields.Char(string='Cashier', readonly=True,
                               help='Cashier of the operation: the employee logged in at the register when '
                                    'the Employees module is used at the point of sale, else the user.')
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, check_company=True)

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
    note = fields.Char(string='Note', help='Free note of the cashier, the only field a manager can edit.')
    statement_line_in_id = fields.Many2one('account.bank.statement.line', string='Received Line', readonly=True,
                                           ondelete='restrict', check_company=True)
    statement_line_out_id = fields.Many2one('account.bank.statement.line', string='Handed Line', readonly=True,
                                            ondelete='restrict', check_company=True)
    cancel_date = fields.Datetime(string='Cancelled On', readonly=True, copy=False)
    cancel_user_id = fields.Many2one('res.users', string='Cancelled By', readonly=True, copy=False)
    statement_line_cancel_in_id = fields.Many2one(
        'account.bank.statement.line', string='Received Reversal Line', readonly=True, copy=False,
        ondelete='restrict', check_company=True,
        help='Statement line handing the notes received back to the customer.')
    statement_line_cancel_out_id = fields.Many2one(
        'account.bank.statement.line', string='Handed Reversal Line', readonly=True, copy=False,
        ondelete='restrict', check_company=True,
        help='Statement line taking back the notes handed to the customer.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pos.nm.exchange') or '/'
        return super().create(vals_list)

    def write(self, vals):
        # The register of operations is a record: only the note can be
        # changed by hand, the rest is written by the operation itself.
        if not self.env.su and set(vals) - {'note'}:
            raise UserError(_("An exchange operation cannot be edited, only its note. "
                              "Cancel the operation instead."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_operation(self):
        raise UserError(_("An exchange operation cannot be deleted. Cancel it instead."))

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
    def _nm_operator(self, config, employee_id=None):
        """Cashier of an operation, decided by the server: the logged-in user
        and, when the point of sale uses the Employees module (pos_hr), the
        employee logged in at the register, checked against the employees
        allowed on that point of sale.

        :return: (employee or None, cashier name, partner of the statement
            lines: the operator, as for the cash moves of the register)
        """
        user = self.env.user
        if not employee_id or not config.module_pos_hr or 'hr.employee' not in self.env:
            return None, user.name, user.partner_id
        employee = self.env['hr.employee'].sudo().search(Domain.AND([
            config._employee_domain(config.current_user_id.id),
            [('id', '=', int(employee_id))],
        ]), limit=1)
        if not employee:
            raise UserError(_("This employee is not allowed to use this Point of Sale."))
        return employee, employee.name, employee.work_contact_id or user.partner_id

    @api.model
    def create_from_ui(self, session_id, currency_in_id, amount_in, currency_out_id, partner_id=None,
                       note=None, employee_id=None):
        """Register: record the operation and post its two statement lines.

        The POS users can only read the operations: the operation is created
        here, with sudo, once every check has passed.

        :param employee_id: employee logged in at the register (pos_hr)
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
        employee, cashier_name, operator = self._nm_operator(config, employee_id)

        exchange = self.sudo().create({
            'session_id': session.id,
            'partner_id': partner.id,
            'user_id': self.env.uid,
            'cashier_name': cashier_name,
            'currency_in_id': currency_in.id,
            'currency_out_id': currency_out.id,
            'note': note or False,
            **{key: quote[key] for key in ('amount_in', 'value_in', 'amount_out', 'value_out', 'commission', 'rate')},
        })
        label_in = _('%(name)s: %(amount)s received', name=exchange.name, amount=currency_in.format(quote['amount_in']))
        label_out = _('%(name)s: %(amount)s handed back', name=exchange.name, amount=currency_out.format(quote['amount_out']))
        line_in = exchange._nm_post_line(
            cash_pm, session, quote['value_in'], account, label_in, operator, currency_in, quote['amount_in'], employee)
        line_out = exchange._nm_post_line(
            cash_pm, session, -quote['value_out'], account, label_out, operator, currency_out, quote['amount_out'],
            employee)
        exchange.write({'statement_line_in_id': line_in.id, 'statement_line_out_id': line_out.id})
        return exchange._nm_receipt_data()

    def _nm_post_line(self, cash_pm, session, amount, account, label, partner, currency, amount_currency,
                      employee=None):
        """Statement line of the cash journal in ``currency`` (a foreign
        line when it is not the currency of the point of sale), like the
        cash moves of POS Multi-Currency Cash: ``partner`` is the operator,
        not the customer, and with pos_hr the line keeps the employee."""
        self.ensure_one()
        config = session.config_id
        if currency == config.currency_id:
            move_lines = cash_pm._create_payment_line(session, amount, account, label, partner)
        else:
            move_lines = cash_pm._create_payment_line(
                session, amount, account, label, partner, currency.id, amount_currency)
            detail = session._nm_get_or_create_detail(currency)
            signed = amount_currency if amount > 0 else -amount_currency
            detail.cash_moves_amount = currency.round(detail.cash_moves_amount + signed)
        line = move_lines.move_id.statement_line_id
        if employee:
            line.employee_id = employee
        return line

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def action_cancel(self):
        """Cancel the operations by reversal (Point of Sale managers only)."""
        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise AccessError(_("Only a Point of Sale manager can cancel an exchange operation."))
        self.check_access('read')
        for exchange in self.sudo():
            exchange._nm_cancel()
        return True

    def _nm_cancel(self):
        """Post two statement lines exactly opposite to those of the
        operation (same amounts in both currencies, same counterpart
        account), while its session is open: the notes received go back to
        the customer, the notes handed back return to the drawer, and the
        commission account is back to its balance before the operation."""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("The operation %s is already cancelled.", self.name))
        session = self.session_id
        if session.state not in ('opened', 'closing_control'):
            raise UserError(_(
                "The operation %(name)s belongs to the closed session %(session)s: an operation can only be "
                "cancelled while its session is open. Record an opposite operation or a cash move instead.",
                name=self.name, session=session.name))
        if not self.statement_line_in_id or not self.statement_line_out_id:
            raise UserError(_("The statement lines of the operation %s are missing: it cannot be reversed.",
                              self.name))
        config = session.config_id
        if self.currency_in_id != config.currency_id:
            balance = config._nm_currency_balance(self.currency_in_id)
            if self.currency_in_id.compare_amounts(self.amount_in, balance) > 0:
                raise UserError(_(
                    "The drawer of %(currency)s holds %(balance)s: %(amount)s cannot be handed back.",
                    currency=self.currency_in_id.name, balance=self.currency_in_id.format(balance),
                    amount=self.currency_in_id.format(self.amount_in)))
        cash_pm = session._nm_cash_payment_method()
        if not cash_pm:
            raise UserError(_("There is no cash payment method for this PoS Session"))
        operator = self.env.user.partner_id
        reversals = []
        for line, currency, label in (
            (self.statement_line_in_id, self.currency_in_id, _(
                '%(name)s cancelled: %(amount)s handed back',
                name=self.name, amount=self.currency_in_id.format(self.amount_in))),
            (self.statement_line_out_id, self.currency_out_id, _(
                '%(name)s cancelled: %(amount)s received back',
                name=self.name, amount=self.currency_out_id.format(self.amount_out))),
        ):
            account = (line.move_id.line_ids.account_id - line.journal_id.default_account_id)[:1]
            reversals.append(self._nm_post_line(
                cash_pm, session, -line.amount, account, label, operator, currency, abs(line.amount_currency)))
        self.write({
            'state': 'cancelled',
            'cancel_date': fields.Datetime.now(),
            'cancel_user_id': self.env.uid,
            'statement_line_cancel_in_id': reversals[0].id,
            'statement_line_cancel_out_id': reversals[1].id,
        })
        session.message_post(body=_(
            "Currency exchange %(name)s cancelled by %(user)s.", name=self.name, user=self.env.user.name))

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
        lines = (self.statement_line_in_id | self.statement_line_out_id
                 | self.statement_line_cancel_in_id | self.statement_line_cancel_out_id)
        return {
            'name': _('Statement Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', lines.ids)],
        }
