# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.tools import float_round
from odoo.tools.misc import formatLang

from .res_partner import ID_DOCUMENT_TYPES

# Identity document sent by the register: field of the operation, field of
# the partner, key sent by the register.
ID_DOCUMENT_FIELDS = [
    ('id_document_type', 'nm_id_document_type', 'type'),
    ('id_document_number', 'nm_id_document_number', 'number'),
    ('id_document_country_id', 'nm_id_document_country_id', 'country_id'),
    ('id_document_expiry', 'nm_id_document_expiry', 'expiry'),
    ('id_document_no_expiry', 'nm_id_document_no_expiry', 'no_expiry'),
    ('id_nationality_id', 'nm_nationality_id', 'nationality_id'),
    ('id_birthdate', 'nm_birthdate', 'birthdate'),
]

# Code of the refusal of an operation whose quote changed since the
# register showed it (context of the error sent to the register).
QUOTE_CHANGED = 'nm_exchange_quote_changed'


class NmQuoteChangedError(UserError):
    """The quote of an operation changed between the popup and the server
    (rates, margin or commission changed): nothing was recorded.

    The register tells it from the other refusals by the ``context`` of
    the error (``{'nm_exchange_error': QUOTE_CHANGED, ...}``), sent with
    the error data, and requests a fresh quote."""

    def __init__(self, message, amount_out=0.0, quoted=0.0):
        super().__init__(message)
        self.context = {'nm_exchange_error': QUOTE_CHANGED, 'amount_out': amount_out, 'quoted': quoted}


# The operation from the point of view of the shop.
OPERATION_TYPES = [
    ('purchase', 'Purchase of foreign currency'),
    ('sale', 'Sale of foreign currency'),
    ('cross', 'Cross exchange'),
]


class PosNmExchange(models.Model):
    """Currency exchange operation at the register: the customer brings
    notes in one cash currency of the point of sale and leaves with another.

    Two statement lines of the cash journal of the session, like a cash in
    and a cash out of POS Multi-Currency Cash: the notes received (in their
    currency, at the cash rate of the point of sale, the buy rate) and the
    notes handed back (in their currency, at the sell rate of the counter).
    Both use the commission income account as counterpart: the difference
    between the two values is the commission, which lands on that account.
    The spread between these rates and the rate of Odoo is the rate margin,
    realized when the foreign drawers are deposited or revalued.
    """
    _name = 'pos.nm.exchange'
    _inherit = ['mail.thread']
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
    customer_name = fields.Char(
        string='Customer Name', readonly=True,
        help='Name of the customer when the operation was recorded: later changes of the contact do not '
             'change it.')
    linked_value = fields.Monetary(
        string='Value with Linked Operations', currency_field='company_currency_id', readonly=True,
        help='Value compared to the identification thresholds: the received value plus the operations '
             'of the customer over the linked operations period of the point of sale.')
    # Frozen copy of the identity document shown by the customer: later
    # changes of the contact do not change the register.
    id_document_type = fields.Selection(
        ID_DOCUMENT_TYPES, string='Identity Document', readonly=True, groups='point_of_sale.group_pos_manager',
        help='Identity document shown by the customer, as recorded with the operation.')
    id_document_number = fields.Char(
        string='Document Number', readonly=True, groups='point_of_sale.group_pos_manager')
    id_document_country_id = fields.Many2one(
        'res.country', string='Issuing Country', readonly=True, groups='point_of_sale.group_pos_manager')
    id_document_expiry = fields.Date(
        string='Document Expiry Date', readonly=True, groups='point_of_sale.group_pos_manager')
    id_document_no_expiry = fields.Boolean(
        string='No Expiry Date', readonly=True, groups='point_of_sale.group_pos_manager',
        help='The identity document shown has no expiry date.')
    id_nationality_id = fields.Many2one(
        'res.country', string='Nationality', readonly=True, groups='point_of_sale.group_pos_manager')
    id_birthdate = fields.Date(string='Date of Birth', readonly=True, groups='point_of_sale.group_pos_manager')

    currency_in_id = fields.Many2one('res.currency', string='Received Currency', required=True, readonly=True)
    amount_in = fields.Monetary(string='Received', currency_field='currency_in_id', readonly=True,
                                help='Notes received from the customer.')
    value_in = fields.Monetary(string='Received Value', currency_field='company_currency_id', readonly=True,
                               help='Value of the notes received at the cash rate of the point of sale '
                                    '(the rate of Odoo with the cash rate margin, or the fixed rate).')
    currency_out_id = fields.Many2one('res.currency', string='Handed Currency', required=True, readonly=True)
    amount_out = fields.Monetary(string='Handed Back', currency_field='currency_out_id', readonly=True,
                                 help='Notes handed to the customer.')
    value_out = fields.Monetary(string='Handed Value', currency_field='company_currency_id', readonly=True,
                                help='Value of the notes handed back at the sell rate of the counter (the '
                                     'rate of Odoo less the exchange sell margin, or the lower fixed rate).')
    commission = fields.Monetary(string='Commission', currency_field='company_currency_id', readonly=True,
                                 help='Received value minus handed value: the commission of the counter, '
                                      'rounding of the notes handed back included.')
    rate_margin = fields.Monetary(
        string='Rate Margin', currency_field='company_currency_id', readonly=True,
        help='Margin earned on the rates: the value of the notes received at the rate of Odoo of '
             'the day less the received value, plus the handed value less the value of the notes '
             'handed back at the rate of Odoo. Realized when the foreign notes are deposited or '
             'revalued; the commission plus the rate margin is the income of the operation.')
    # 12 decimals: the rate of 1 VND or 1 IDR in euros has 4 or 5 zeros
    # after the decimal point.
    rate = fields.Float(string='Rate', digits=(16, 12), readonly=True,
                        help='Units of the handed currency for one unit of the received currency, '
                             'commission included.')
    rate_label = fields.Char(string='Rate Applied', compute='_compute_rate_label',
                             help='Rate of the operation in the direction where it is at least 1, '
                                  'commission included.')
    note = fields.Char(string='Note', help='Free note of the cashier, the only field a manager can edit.')
    operation_type = fields.Selection(
        OPERATION_TYPES, string='Operation Type', compute='_compute_operation_type', store=True,
        help='The operation from the point of view of the shop: purchase of foreign currency (foreign '
             'notes received), sale of foreign currency (foreign notes handed back) or cross exchange '
             '(two foreign currencies).')
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
    uuid = fields.Char(
        string='Register Identifier', readonly=True, copy=False,
        help='Identifier of the operation sent by the register: an operation confirmed again after '
             'a lost connection is recorded only once.')

    _uuid_unique = models.Constraint(
        'unique (uuid)', 'An exchange operation with this register identifier already exists.')

    @api.depends('rate', 'currency_in_id', 'currency_out_id')
    def _compute_rate_label(self):
        for exchange in self:
            exchange.rate_label = self._nm_rate_label(exchange.currency_in_id, exchange.currency_out_id, exchange.rate)

    @api.depends('currency_in_id', 'currency_out_id', 'company_currency_id')
    def _compute_operation_type(self):
        for exchange in self:
            if exchange.currency_out_id == exchange.company_currency_id:
                exchange.operation_type = 'purchase'
            elif exchange.currency_in_id == exchange.company_currency_id:
                exchange.operation_type = 'sale'
            else:
                exchange.operation_type = 'cross'

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
        # Logged in the chatter whatever the optional tracking module, like
        # the rates of POS Multi-Currency Cash.
        old_notes = {exchange.id: exchange.note for exchange in self} if 'note' in vals else {}
        result = super().write(vals)
        for exchange in self.filtered(lambda e: e.id in old_notes and old_notes[e.id] != e.note):
            exchange.message_post(body=_("Note: %(old)s -> %(new)s",
                                         old=old_notes[exchange.id] or '', new=exchange.note or ''))
        return result

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
    def _nm_market_value(self, config, currency, amount, date=None):
        """Value in the POS currency of ``amount`` in ``currency`` at the rate
        of Odoo, without margin."""
        if currency == config.currency_id:
            return amount
        rate = config._nm_odoo_rate(currency, date)
        return config.currency_id.round(amount / rate) if rate else 0.0

    @api.model
    def _nm_rate_margin(self, config, currency_in, amount_in, value_in, currency_out, amount_out, value_out,
                        date=None):
        """Margin earned on the rates of an operation: the notes received are
        worth more at the rate of Odoo than their received value, the notes
        handed back less than their handed value."""
        return config.currency_id.round(
            self._nm_market_value(config, currency_in, amount_in, date) - value_in
            + value_out - self._nm_market_value(config, currency_out, amount_out, date))

    @api.model
    def _nm_quote(self, config, currency_in, amount_in, currency_out):
        """Amounts of an operation: value received, commission, value and
        notes handed back.

        The notes received are valued at the cash rate of the point of sale
        (the buy rate), the notes handed back at the sell rate of the counter.
        The notes handed back are rounded once, down, to the smallest coin or
        note of their currency: the change rounding of a foreign currency,
        the cash rounding of the point of sale for its own currency, else the
        rounding of the currency. The remainder stays in the commission,
        which is never below the configured one.
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
            rate_out = 1.0
        else:
            rate_out = config._nm_exchange_sell_rate(currency_out)
        amount_out = float_round(value_out * rate_out, precision_rounding=self._nm_change_step(config, currency_out),
                                 rounding_method='DOWN')
        value_out = company_currency.round(amount_out / rate_out) if rate_out else 0.0
        return {
            'amount_in': amount_in,
            'value_in': value_in,
            'amount_out': amount_out,
            'value_out': value_out,
            'commission': company_currency.round(value_in - value_out),
            'rate_margin': self._nm_rate_margin(
                config, currency_in, amount_in, value_in, currency_out, amount_out, value_out),
            'rate': (amount_out / amount_in) if amount_in else 0.0,
        }

    @api.model
    def _nm_linked_value(self, config, value_in, partner):
        """Value compared to the identification thresholds: ``value_in``
        plus the operations done by ``partner`` over the linked operations
        period, at every point of sale of the company, in the currency of
        ``config``."""
        if not partner or config.nm_exchange_linked_days <= 0:
            return value_in
        since = fields.Datetime.now() - timedelta(days=config.nm_exchange_linked_days)
        groups = self.sudo()._read_group([
            ('partner_id', '=', partner.id),
            ('company_id', '=', config.company_id.id),
            ('state', '=', 'done'),
            ('date', '>=', since),
        ], ['config_id'], ['value_in:sum'])
        today = fields.Date.context_today(self)
        linked = sum(
            other.currency_id._convert(value, config.currency_id, config.company_id, today)
            for other, value in groups)
        return config.currency_id.round(value_in + linked)

    @api.model
    def _nm_identification(self, config, value_in, partner):
        """What the operation needs to identify its customer.

        :return: dict: ``linked_value`` (see _nm_linked_value),
            ``customer_required``, ``document_required`` and
            ``threshold_exceeded`` (the linked value is above a threshold)
        """
        currency = config.currency_id
        linked_value = self._nm_linked_value(config, value_in, partner)

        def above(threshold):
            return bool(threshold) and currency.compare_amounts(linked_value, threshold) > 0

        document_required = above(config.nm_exchange_document_threshold)
        threshold_exceeded = document_required or above(config.nm_exchange_customer_threshold)
        return {
            'linked_value': linked_value,
            'customer_required': config.nm_exchange_customer_always or threshold_exceeded,
            'document_required': document_required,
            'threshold_exceeded': threshold_exceeded,
        }

    @api.model
    def _nm_identification_error(self, config, identification, partner, document):
        """Refusal of an operation whose customer is not identified as
        required, else an empty string.

        :param document: identity document of the operation (values of its
            fields, see _nm_document_values)
        """
        currency = config.currency_id
        linked = identification['linked_value']
        days = config.nm_exchange_linked_days
        if identification['document_required']:
            threshold = currency.format(config.nm_exchange_document_threshold)
            if not partner:
                return _("A customer with an identity document must be identified for an exchange operation "
                         "above %s.", threshold)
            if not document.get('id_document_type') and not document.get('id_document_number'):
                if days > 0:
                    return _(
                        "The identity document of the customer is required: with the operations of the last "
                        "%(days)s days, %(amount)s were exchanged, above %(threshold)s.",
                        days=days, amount=currency.format(linked), threshold=threshold)
                return _("The identity document of the customer is required for an exchange operation above "
                         "%s.", threshold)
            return self._nm_document_error(document)
        if identification['customer_required'] and not partner:
            if config.nm_exchange_customer_always:
                return _("A customer must be identified for every exchange operation at this Point of Sale.")
            return _("A customer must be identified for an exchange operation above %s.",
                     currency.format(config.nm_exchange_customer_threshold))
        return ''

    @api.model
    def _nm_document_error(self, document):
        """Refusal of an identity document (values of the operation
        fields), else an empty string."""
        if not document.get('id_document_type') or not document.get('id_document_number'):
            return _("Enter the type and the number of the identity document of the customer.")
        expiry = document.get('id_document_expiry')
        if not expiry:
            if document.get('id_document_no_expiry'):
                return ''
            return _("Enter the expiry date of the identity document of the customer, or tick No expiry date.")
        if expiry < fields.Date.context_today(self):
            return _("The identity document of the customer expired on %s: it cannot be accepted.",
                     fields.Date.to_string(expiry))
        return ''

    @api.model
    def _nm_document_values(self, partner, document=None):
        """Identity document of the operation: the one typed or confirmed
        at the register (``document``, keys of ID_DOCUMENT_FIELDS), else the
        one of ``partner``. Values of the fields of the operation.

        The register only shows the end of the number recorded on the
        customer: the fields left empty keep the values of the customer when
        the document is the same (same type, number not typed again), else
        only the nationality and the date of birth do. The expiry date and
        "No expiry date" go together: an expiry date typed clears the box,
        the box ticked clears the expiry date, and the pair recorded on the
        customer is kept only when neither is given."""
        if document is None:
            partner = partner.sudo()
            return {
                field: partner[partner_field].id if partner_field.endswith('_id') else partner[partner_field]
                for field, partner_field, _key in ID_DOCUMENT_FIELDS}
        countries = self.env['res.country']
        values = {}
        for field, _partner_field, key in ID_DOCUMENT_FIELDS:
            value = document.get(key) or False
            if field.endswith('_id'):
                value = value and countries.browse(int(value)).exists().id
            elif field in ('id_document_expiry', 'id_birthdate'):
                try:
                    value = value and fields.Date.to_date(value)
                except ValueError:
                    raise UserError(_("Invalid date in the identity document of the customer: %s", value)) from None
            elif field == 'id_document_no_expiry':
                value = value is True or value in ('1', 'true', 'True')
            elif isinstance(value, str):
                value = value.strip()
            values[field] = value or False
        if values['id_document_type'] not in dict(ID_DOCUMENT_TYPES):
            values['id_document_type'] = False
        if values['id_document_no_expiry']:
            values['id_document_expiry'] = False
        expiry_given = bool(values['id_document_expiry'] or values['id_document_no_expiry'])
        stored = self._nm_document_values(partner)
        same_document = (values['id_document_type'] in (False, stored['id_document_type'])
                         and values['id_document_number'] in (False, stored['id_document_number']))
        for field, value in values.items():
            if field in ('id_document_expiry', 'id_document_no_expiry') and expiry_given:
                continue
            if not value and (same_document or field in ('id_nationality_id', 'id_birthdate')):
                values[field] = stored[field]
        return values

    @api.model
    def _nm_change_step(self, config, currency):
        """Smallest coin or note of ``currency`` handed back by the counter,
        the step the quote rounds the notes handed back down to: the change
        rounding of a foreign currency, the cash rounding of the point of
        sale for its own currency; at least the rounding of the currency."""
        if currency == config.currency_id:
            step = config.rounding_method.rounding if config.cash_rounding else 0.0
        else:
            step = config._nm_get_currency_setting(currency).change_rounding
        return max(step, currency.rounding)

    @api.model
    def _nm_payment_step(self, config, currency):
        """Smallest coin or note of ``currency`` taken from the customer, as
        the register checks it (getPaymentStep of POS Multi-Currency Cash):
        the payment rounding of a foreign currency, else its change rounding
        when the remainder of the change is kept as rounding; the cash
        rounding of the point of sale for its own currency; at least the
        rounding of the currency."""
        if currency == config.currency_id:
            step = config.rounding_method.rounding if config.cash_rounding else 0.0
        else:
            setting = config._nm_get_currency_setting(currency)
            step = setting.payment_rounding
            if not step and setting.change_rest_mode == 'rounding':
                step = setting.change_rounding
        return max(step, currency.rounding)

    @api.model
    def _nm_reverse_amount_in(self, config, currency_in, currency_out, amount_out):
        """Smallest amount received, a multiple of the payment step of
        ``currency_in``, whose quote hands back at least ``amount_out``.

        The amount handed back by the quote never decreases when the amount
        received grows: double the amount until it is enough, then bisect.
        """
        step = self._nm_payment_step(config, currency_in)

        def enough(units):
            quote = self._nm_quote(config, currency_in, units * step, currency_out)
            return currency_out.compare_amounts(quote['amount_out'], amount_out) >= 0

        low, high = 0, 1
        while not enough(high):
            if high >= 2 ** 40:
                raise UserError(_(
                    "No amount received in %(currency)s hands back %(amount)s.",
                    currency=currency_in.name, amount=currency_out.format(amount_out)))
            low, high = high, high * 2
        while high - low > 1:
            middle = (low + high) // 2
            if enough(middle):
                high = middle
            else:
                low = middle
        return currency_in.round(high * step)

    @api.model
    def _nm_check_currencies(self, config, currency_in, currency_out):
        currencies = config._nm_exchange_currencies()
        if currency_in not in currencies or currency_out not in currencies:
            raise UserError(_("This currency is not accepted at the exchange counter of this Point of Sale."))
        if currency_in == currency_out:
            raise UserError(_("The received and handed currencies must differ."))
        if not config.nm_exchange_enabled:
            raise UserError(_("The currency exchange counter is disabled on this Point of Sale."))

    @api.model
    def _nm_check_operation(self, config, currency_in, amount_in, currency_out):
        self._nm_check_currencies(config, currency_in, currency_out)
        if currency_in.compare_amounts(amount_in or 0.0, 0.0) <= 0:
            raise UserError(_("The received amount must be positive."))

    @api.model
    def _nm_check_quote(self, quote, currency_out):
        if currency_out.compare_amounts(quote['amount_out'], 0.0) <= 0:
            raise UserError(_("The amount is too small for an exchange operation in %s: once the commission is "
                              "deducted, no note can be handed back.", currency_out.name))

    @api.model
    def _nm_drawer_error(self, currency, amount, available):
        """Refusal when ``amount`` is more than the drawer of ``currency``
        holds (``available``), else an empty string."""
        if currency.compare_amounts(amount, available) > 0:
            return _(
                "The drawer of %(currency)s holds %(balance)s: %(amount)s cannot be handed back.",
                currency=currency.name, balance=currency.format(available), amount=currency.format(amount))
        return ''

    @api.model
    def _nm_check_drawer(self, session, currency, amount):
        """Refuse to hand back more notes than the drawer of ``currency``
        holds, as counted by the closing control."""
        error = self._nm_drawer_error(currency, amount, session._nm_expected_cash(currency))
        if error:
            raise UserError(error)

    @api.model
    def _nm_check_pos_user(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You don't have the access rights to use the exchange counter."))

    @api.model
    def _nm_quote_records(self, config_id, currency_in_id, currency_out_id):
        """Point of sale and currencies of a quote asked by the register."""
        self._nm_check_pos_user()
        config = self.env['pos.config'].browse(int(config_id)).exists()
        currency_in = self.env['res.currency'].browse(int(currency_in_id)).exists()
        currency_out = self.env['res.currency'].browse(int(currency_out_id)).exists()
        if not config or not currency_in or not currency_out:
            raise UserError(_("Unknown point of sale or currency."))
        return config, currency_in, currency_out

    @api.model
    def _nm_counter_config(self, config_id):
        """Point of sale of the register, readable by the cashier, whose
        exchange counter is enabled."""
        self._nm_check_pos_user()
        config = self.env['pos.config'].browse(int(config_id)).exists()
        if not config:
            raise UserError(_("Unknown point of sale or currency."))
        config.check_access('read')
        if not config.nm_exchange_enabled:
            raise UserError(_("The currency exchange counter is disabled on this Point of Sale."))
        return config

    @api.model
    def _nm_partner(self, partner_id):
        """Customer selected at the register, readable by the cashier: its
        operations and its identity document are then read with sudo."""
        partner = self.env['res.partner'].browse(int(partner_id)).exists() if partner_id else self.env['res.partner']
        partner.check_access('read')
        return partner

    @api.model
    def get_quote(self, config_id, currency_in_id, amount_in, currency_out_id, partner_id=None):
        """Register: amounts of the operation for the popup, the drawer of
        the currency handed back in the open session, and the identification
        of the customer (``partner_id``, the customer selected), checked as
        when the operation is recorded."""
        config, currency_in, currency_out = self._nm_quote_records(config_id, currency_in_id, currency_out_id)
        self._nm_check_operation(config, currency_in, amount_in, currency_out)
        quote = self._nm_quote(config, currency_in, float(amount_in), currency_out)
        self._nm_check_quote(quote, currency_out)
        quote.update(self._nm_identification(config, quote['value_in'], self._nm_partner(partner_id)))
        # The exchanges of a customer are not shown to the cashier, unless
        # they are why the customer or the document is required.
        if not quote.pop('threshold_exceeded'):
            quote['linked_value'] = quote['value_in']
        quote.update({
            'linked_value_formatted': config.currency_id.format(quote['linked_value']),
            'amount_in_formatted': currency_in.format(quote['amount_in']),
            'amount_out_formatted': currency_out.format(quote['amount_out']),
            'commission_formatted': config.currency_id.format(quote['commission']),
            'value_in_formatted': config.currency_id.format(quote['value_in']),
            'rate_label': self._nm_rate_label(currency_in, currency_out, quote['rate']),
            'drawer_balance_formatted': '',
            'drawer_error': '',
        })
        session = config.current_session_id
        if session:
            available = session._nm_expected_cash(currency_out)
            quote.update({
                'drawer_balance_formatted': currency_out.format(available),
                'drawer_error': self._nm_drawer_error(currency_out, quote['amount_out'], available),
            })
        return quote

    @api.model
    def get_reverse_quote(self, config_id, currency_in_id, currency_out_id, amount_out, partner_id=None):
        """Register: the customer asks for ``amount_out``; quote of the
        smallest amount received, rounded up to the coins and notes of its
        currency, handing back at least that much. The operation is then
        recorded from this amount received, as any other."""
        config, currency_in, currency_out = self._nm_quote_records(config_id, currency_in_id, currency_out_id)
        self._nm_check_currencies(config, currency_in, currency_out)
        amount_out = float(amount_out or 0.0)
        if currency_out.compare_amounts(amount_out, 0.0) <= 0:
            raise UserError(_("The amount handed back must be positive."))
        amount_in = self._nm_reverse_amount_in(config, currency_in, currency_out, amount_out)
        return self.get_quote(config.id, currency_in.id, amount_in, currency_out.id, partner_id)

    @api.model
    def get_customer_document(self, config_id, partner_id):
        """Register: identity document recorded on the customer selected,
        for the cashier to confirm or update it in the popup, at a point of
        sale whose counter asks for identity documents. Read with sudo (the
        POS users do not read these fields of the contacts otherwise) and in
        part only: type, issuing country, expiry date (or no expiry date)
        and the last 4 characters of the number."""
        config = self._nm_counter_config(config_id)
        if not config.nm_exchange_document_threshold:
            raise UserError(_("This Point of Sale does not ask for identity documents."))
        values = self._nm_document_values(self._nm_partner(partner_id))
        number = values['id_document_number'] or ''
        return {
            'type': values['id_document_type'] or False,
            'number_masked': f"****{number[-4:]}" if number else '',
            'country_id': values['id_document_country_id'] or False,
            'expiry': fields.Date.to_string(values['id_document_expiry']) if values['id_document_expiry'] else False,
            'no_expiry': bool(values['id_document_no_expiry']),
        }

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
    def create_from_ui(self, session_id, currency_in_id, amount_in, currency_out_id, partner_id=None, *,
                       note=None, employee_id=None, amount_out=None, uuid=None, document=None):
        """Register: record the operation and post its two statement lines.

        The POS users can only read the operations: the operation is created
        here, with sudo, once every check has passed.

        :param employee_id: employee logged in at the register (pos_hr)
        :param amount_out: notes to hand back shown to the cashier by the
            quote: the operation is refused (NmQuoteChangedError) when the
            rates or the commission changed since
        :param uuid: identifier of the operation generated by the register:
            when it was already recorded (the response was lost and the
            cashier confirms again), nothing is recorded twice
        :param document: identity document of the customer typed or
            confirmed at the register (keys of ID_DOCUMENT_FIELDS), when
            required: saved on the customer and frozen on the operation;
            without it, the document of the customer is used
        :return: the data of the exchange receipt
        """
        self._nm_check_pos_user()
        if uuid:
            recorded = self.sudo().search([('uuid', '=', uuid), ('session_id', '=', int(session_id))], limit=1)
            if recorded:
                recorded._nm_check_same_operation(currency_in_id, amount_in, currency_out_id, partner_id, amount_out)
                return recorded._nm_receipt_data()
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
        self._nm_check_quote(quote, currency_out)
        if amount_out is not None and currency_out.compare_amounts(quote['amount_out'], float(amount_out)):
            raise NmQuoteChangedError(_(
                "The quote changed: %(amount)s is now handed back instead of %(quoted)s. Check the amount "
                "again before confirming.",
                amount=currency_out.format(quote['amount_out']), quoted=currency_out.format(float(amount_out))),
                amount_out=quote['amount_out'], quoted=float(amount_out))
        partner = self._nm_partner(partner_id)
        identification = self._nm_identification(config, quote['value_in'], partner)
        document_values = {}
        if identification['document_required'] and partner:
            document_values = self._nm_document_values(partner, document)
        error = self._nm_identification_error(config, identification, partner, document_values)
        if error:
            raise UserError(error)
        document_changed = document is not None and document_values \
            and document_values != self._nm_document_values(partner)
        self._nm_check_drawer(session, currency_out, quote['amount_out'])
        employee, cashier_name, operator = self._nm_operator(config, employee_id)

        # The cashier does not follow the operations: the receipt e-mailed
        # to the customer is not sent to the cashier too.
        exchange = self.sudo().with_context(mail_create_nosubscribe=True, mail_create_nolog=True).create({
            'session_id': session.id,
            'partner_id': partner.id,
            'customer_name': partner.name or False,
            'linked_value': identification['linked_value'],
            **document_values,
            'user_id': self.env.uid,
            'cashier_name': cashier_name,
            'currency_in_id': currency_in.id,
            'currency_out_id': currency_out.id,
            'note': note or False,
            'uuid': uuid or False,
            **{key: quote[key] for key in (
                'amount_in', 'value_in', 'amount_out', 'value_out', 'commission', 'rate_margin', 'rate')},
        })
        label_in = _('%(name)s: %(amount)s received', name=exchange.name, amount=currency_in.format(quote['amount_in']))
        label_out = _('%(name)s: %(amount)s handed back', name=exchange.name, amount=currency_out.format(quote['amount_out']))
        line_in = exchange._nm_post_line(
            cash_pm, session, quote['value_in'], account, label_in, operator, currency_in, quote['amount_in'], employee)
        line_out = exchange._nm_post_line(
            cash_pm, session, -quote['value_out'], account, label_out, operator, currency_out, quote['amount_out'],
            employee)
        exchange.write({'statement_line_in_id': line_in.id, 'statement_line_out_id': line_out.id})
        if document_changed:
            exchange._nm_save_customer_document(partner, document_values)
        return exchange._nm_receipt_data()

    def _nm_check_same_operation(self, currency_in_id, amount_in, currency_out_id, partner_id, amount_out):
        """An operation confirmed again with the identifier of this one (its
        response was lost) must be this operation: refused when the cashier
        changed the currencies, the amounts or the customer in between."""
        self.ensure_one()
        currency_in, currency_out = self.currency_in_id, self.currency_out_id
        same = (
            currency_in.id == int(currency_in_id) and currency_out.id == int(currency_out_id)
            and not currency_in.compare_amounts(float(amount_in or 0.0), self.amount_in)
            and (amount_out is None or not currency_out.compare_amounts(float(amount_out), self.amount_out))
            and self.partner_id.id == (int(partner_id) if partner_id else False)
        )
        if not same:
            raise UserError(_(
                "This operation was already recorded as %s with other amounts: close the popup and start a new "
                "operation.", self.name))

    def _nm_save_customer_document(self, partner, document_values):
        """Save the identity document of the operation on its customer, with
        a message on the contact (masked number). The contact of an internal
        user, archived or not, is only changed by a Point of Sale manager:
        else the document stays on the operation alone. A portal or public
        account does not protect its contact: it is a customer."""
        self.ensure_one()
        partner = partner.sudo()
        internal_users = partner.with_context(active_test=False).user_ids.filtered(lambda user: not user.share)
        if internal_users and not self.env.user.has_group('point_of_sale.group_pos_manager'):
            return
        partner.write({partner_field: document_values[field] for field, partner_field, _key in ID_DOCUMENT_FIELDS})
        partner.message_post(
            body=_("Identity document updated by %(user)s with the exchange operation %(name)s: %(document)s",
                   user=self.env.user.name, name=self.name, document=self._nm_masked_document()),
            subtype_xmlid='mail.mt_note')

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
        self._nm_check_drawer(session, self.currency_in_id, self.amount_in)
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
        message = _("Currency exchange %(name)s cancelled by %(user)s.", name=self.name, user=self.env.user.name)
        session.message_post(body=message)
        self.message_post(body=message)

    @api.model
    def _nm_local_datetime(self, value):
        """``value`` in the time zone of the user, with the seconds."""
        return fields.Datetime.context_timestamp(self, value).strftime('%Y-%m-%d %H:%M:%S') if value else ''

    def _nm_receipt_data(self, copy=False):
        """Content of the exchange receipt, printed at the register and in
        the PDF of the operation.

        :param copy: the receipt is printed again: marked as a copy
        """
        self.ensure_one()
        company_currency = self.company_currency_id
        config = self.config_id
        return {
            'id': self.id,
            'name': self.name,
            'date': self._nm_local_datetime(self.date),
            'operation_type': dict(self._fields['operation_type']._description_selection(self.env)).get(
                self.operation_type, ''),
            'licence': config.nm_exchange_licence or '',
            'receipt_header': config.receipt_header or '',
            'receipt_footer': config.receipt_footer or '',
            'cashier_name': self.cashier_name or '',
            'partner_name': self.customer_name or '',
            'id_document': self._nm_masked_document(),
            'currency_in': self.currency_in_id.name,
            'currency_out': self.currency_out_id.name,
            'label_in': _('Received (%s)', self.currency_in_id.name),
            'label_out': _('Handed back (%s)', self.currency_out_id.name),
            'amount_in': self.currency_in_id.format(self.amount_in),
            'amount_out': self.currency_out_id.format(self.amount_out),
            'value_in': company_currency.format(self.value_in),
            'commission': company_currency.format(self.commission),
            'rate_label': self.rate_label,
            'note': self.note or '',
            'cancelled': self.state == 'cancelled',
            'cancel_date': self._nm_local_datetime(self.cancel_date),
            'copy': copy,
        }

    @api.model
    def get_session_operations(self, session_id):
        """Register: operations of the session, the latest first, to print
        their receipt again."""
        self._nm_check_pos_user()
        operation_types = dict(self._fields['operation_type']._description_selection(self.env))
        return [{
            'id': exchange.id,
            'name': exchange.name,
            'date': self._nm_local_datetime(exchange.date),
            'operation_type': operation_types.get(exchange.operation_type, ''),
            'partner_name': exchange.customer_name or '',
            'amount_in': exchange.currency_in_id.format(exchange.amount_in),
            'amount_out': exchange.currency_out_id.format(exchange.amount_out),
            'cancelled': exchange.state == 'cancelled',
        } for exchange in self.search([('session_id', '=', int(session_id))])]

    @api.model
    def get_receipt(self, exchange_id):
        """Register: receipt of an operation printed again, as a copy, with
        its cancellation if it was cancelled since."""
        self._nm_check_pos_user()
        exchange = self.browse(int(exchange_id)).exists()
        if not exchange:
            raise UserError(_("Unknown exchange operation."))
        exchange.check_access('read')
        return exchange._nm_receipt_data(copy=True)

    @api.model
    def get_rate_board(self, config_id):
        """Register: exchange rates of the counter (see pos.config._nm_rate_board)."""
        self._nm_check_pos_user()
        config = self.env['pos.config'].browse(int(config_id)).exists()
        if not config:
            raise UserError(_("Unknown point of sale or currency."))
        config.check_access('read')
        return config._nm_rate_board()

    def action_send_mail(self):
        """E-mail the receipt of the operation (PDF attached) to its customer."""
        self.ensure_one()
        template = self.env.ref('pos_nm_currency_exchange.mail_template_pos_nm_exchange', raise_if_not_found=False)
        return {
            'name': _('Send Exchange Receipt'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_model': self._name,
                'default_res_ids': self.ids,
                'default_template_id': template.id if template else False,
                'default_composition_mode': 'comment',
                'force_email': True,
            },
        }

    def _nm_masked_document(self):
        """Identity document as printed on the receipt: its type and the
        last 4 characters of its number only."""
        self.ensure_one()
        exchange = self.sudo()
        if not exchange.id_document_type:
            return ''
        label = dict(exchange._fields['id_document_type']._description_selection(self.env))[exchange.id_document_type]
        number = (exchange.id_document_number or '')[-4:]
        return f"{label} ****{number}" if number else label

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
