# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

from .pos_nm_note_move import _nm_note_key

TRANSFER_STATES = [
    ('draft', 'Draft'),
    ('sent', 'In Transit'),
    ('received', 'Received'),
    ('cancelled', 'Cancelled'),
]
# Fields of a transfer that can still be changed once it is sent: the rest
# is written by the transfer itself.
TRANSFER_FREE_FIELDS = {'note'}
# Fields written only by the transfer itself, when the notes are sent,
# received or cancelled: never by hand, whatever the state.
TRANSFER_SYSTEM_FIELDS = {
    'name', 'state', 'value', 'notes', 'uuid', 'note_move_ids',
    'session_from_id', 'session_to_id',
    'statement_line_from_id', 'statement_line_to_id', 'statement_line_cancel_id',
    'sent_date', 'sent_user_id', 'received_date', 'received_user_id', 'cancel_date', 'cancel_user_id',
}
OPEN_SESSION_STATES = ('opened', 'closing_control')


class PosNmExchangeTransfer(models.Model):
    """Notes moved from the drawer of one counter of an exchange office to
    the drawer of another counter of the same office.

    Sending posts a cash out on the open session of the sending counter and
    receiving a cash in of the same value on the open session of the
    receiving counter, both with the transit account of the office as
    counterpart: the notes in transit are the balance of that account. When
    the notes are tracked by denomination, the transfer moves them out of
    the stock of the sending drawer and into the stock of the receiving one.

    Once sent, a transfer is never edited (but its note) nor deleted: it is
    received, or cancelled by a cash in on the sending session while that
    session is open. The amount received is the amount sent: a difference
    is found by the closing count of the receiving drawer.
    """
    _name = 'pos.nm.exchange.transfer'
    _inherit = ['mail.thread']
    _description = 'Note Transfer'
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(string='Reference', required=True, readonly=True, default='/', copy=False,
                       help='Gapless reference given when the notes are sent.')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency')
    office_id = fields.Many2one('pos.nm.exchange.office', string='Exchange Office', required=True, index=True,
                                check_company=True, ondelete='restrict')
    config_from_id = fields.Many2one(
        'pos.config', string='From Counter', required=True, index=True, check_company=True, ondelete='restrict',
        domain="[('nm_exchange_office_id', '=', office_id)]")
    config_to_id = fields.Many2one(
        'pos.config', string='To Counter', required=True, index=True, check_company=True, ondelete='restrict',
        domain="[('nm_exchange_office_id', '=', office_id), ('id', '!=', config_from_id)]")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        help='Cash currency of both counters: the currency of the points of sale or a foreign currency of the '
             'cash payment methods of both.')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', tracking=True)
    value = fields.Monetary(
        string='Value', currency_field='company_currency_id', readonly=True, copy=False,
        help='Value booked on the transit account, in the currency of the company, frozen when the notes are '
             'sent: the amount itself in the currency of the points of sale, else the amount at the rate of '
             'Odoo of the day, like the cash moves of POS Multi-Currency Cash.')
    state = fields.Selection(TRANSFER_STATES, string='Status', required=True, readonly=True, default='draft',
                             index=True, tracking=True, copy=False)
    session_from_id = fields.Many2one('pos.session', string='Sending Session', readonly=True, copy=False,
                                      index='btree_not_null', ondelete='restrict', check_company=True)
    session_to_id = fields.Many2one('pos.session', string='Receiving Session', readonly=True, copy=False,
                                    index='btree_not_null', ondelete='restrict', check_company=True)
    statement_line_from_id = fields.Many2one(
        'account.bank.statement.line', string='Sent Line', readonly=True, copy=False, ondelete='restrict',
        check_company=True, help='Cash out of the sending session.')
    statement_line_to_id = fields.Many2one(
        'account.bank.statement.line', string='Received Line', readonly=True, copy=False, ondelete='restrict',
        check_company=True, help='Cash in of the receiving session.')
    statement_line_cancel_id = fields.Many2one(
        'account.bank.statement.line', string='Cancellation Line', readonly=True, copy=False, ondelete='restrict',
        check_company=True, help='Cash in of the sending session putting the notes back in its drawer.')
    sent_date = fields.Datetime(string='Sent On', readonly=True, copy=False)
    sent_user_id = fields.Many2one('res.users', string='Sent By', readonly=True, copy=False)
    received_date = fields.Datetime(string='Received On', readonly=True, copy=False)
    received_user_id = fields.Many2one('res.users', string='Received By', readonly=True, copy=False)
    cancel_date = fields.Datetime(string='Cancelled On', readonly=True, copy=False)
    cancel_user_id = fields.Many2one('res.users', string='Cancelled By', readonly=True, copy=False)
    note = fields.Text(string='Note')
    notes = fields.Json(
        string='Notes by Denomination', copy=False,
        help='Coins and notes transferred by denomination ({value: quantity}), adding up to the amount: counted '
             'by the sending counter when it tracks the notes of the currency, else by the receiving counter '
             'when it tracks them.')
    notes_label = fields.Char(string='Coins and Notes', compute='_compute_notes_label')
    note_move_ids = fields.One2many('pos.nm.note.move', 'transfer_id', string='Note Moves', readonly=True)
    uuid = fields.Char(
        string='Register Identifier', readonly=True, copy=False,
        help='Identifier of the transfer sent by the register: a transfer confirmed again after a lost '
             'connection is recorded only once.')

    _uuid_unique = models.Constraint(
        'unique (uuid)', 'A note transfer with this register identifier already exists.')
    _amount_positive = models.Constraint(
        'CHECK (amount > 0)', 'The amount of a note transfer must be positive.')

    @api.depends('notes', 'currency_id')
    def _compute_notes_label(self):
        for transfer in self:
            transfer.notes_label = transfer._nm_notes_label()

    @api.constrains('office_id', 'config_from_id', 'config_to_id', 'currency_id')
    def _check_counters(self):
        for transfer in self:
            transfer._nm_check_counters()

    def _nm_check_counters(self):
        """Both counters belong to the office, differ, use the currency of
        the office, and both take the currency of the transfer in cash."""
        self.ensure_one()
        office = self.office_id
        if self.config_from_id == self.config_to_id:
            raise ValidationError(_("The notes cannot be transferred to the counter that sends them."))
        for config in self.config_from_id | self.config_to_id:
            if config.nm_exchange_office_id != office:
                raise ValidationError(_("The counter %(config)s is not a counter of the exchange office %(office)s.",
                                        config=config.name, office=office.name))
            if config.currency_id != office.currency_id:
                raise ValidationError(_("The counter %(config)s does not use the currency of the exchange office "
                                        "%(office)s.", config=config.name, office=office.name))
            if self.currency_id not in config._nm_exchange_currencies():
                raise ValidationError(_("The counter %(config)s does not take %(currency)s in cash.",
                                        config=config.name, currency=self.currency_id.name))

    @api.model
    def _nm_check_system_fields(self, vals, create=False):
        """Refuse the fields written by the transfer itself (state, number,
        value, sessions, lines...) outside the transfer: a transfer is only
        sent, received or cancelled by its actions. A new transfer may
        only carry the defaults of these fields."""
        if self.env.su:
            return
        names = set(vals) & TRANSFER_SYSTEM_FIELDS
        if create:
            defaults = {'name': '/', 'state': 'draft'}
            names = {name for name in names
                     if not (vals[name] == defaults.get(name) or (name == 'note_move_ids' and not vals[name]))}
        if names:
            labels = sorted(self._fields[name]._description_string(self.env) for name in names)
            raise UserError(_("These fields of a note transfer are set when the notes are sent, received or "
                              "cancelled: %s.", ', '.join(labels)))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._nm_check_system_fields(vals, create=True)
            if vals.get('office_id') and not vals.get('company_id'):
                vals['company_id'] = self.env['pos.nm.exchange.office'].browse(vals['office_id']).company_id.id
        return super().create(vals_list)

    def write(self, vals):
        # A transfer sent is a record of the drawers: only its note can be
        # changed by hand, the rest is written by the transfer itself.
        self._nm_check_system_fields(vals)
        if not self.env.su and set(vals) - TRANSFER_FREE_FIELDS and any(t.state != 'draft' for t in self):
            raise UserError(_("A note transfer cannot be edited once sent, only its note. Cancel it instead."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_sent(self):
        if any(transfer.state != 'draft' for transfer in self):
            raise UserError(_("Only a draft note transfer can be deleted. Cancel it instead."))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _nm_notes_label(self):
        """Coins and notes of the transfer: "2 x €50, 1 x €20" (empty when
        not counted by denomination)."""
        self.ensure_one()
        notes = []
        for key, quantity in (self.notes or {}).items():
            try:
                notes.append((float(key), int(quantity)))
            except (TypeError, ValueError):
                continue
        return ', '.join(f"{quantity} x {self.currency_id.format(value)}"
                         for value, quantity in sorted(notes, reverse=True) if quantity)

    def _nm_note_quantities(self):
        """Notes of the transfer as [(value, quantity)], the largest first."""
        self.ensure_one()
        return sorted(((float(key), int(quantity)) for key, quantity in (self.notes or {}).items() if quantity),
                      reverse=True)

    def _nm_open_session(self, config, session=None):
        """Open session of ``config`` (``session`` when given: it must be
        one of that counter)."""
        session = session or config.current_session_id
        if not session or session.config_id != config or session.state not in OPEN_SESSION_STATES:
            raise UserError(_("The counter %s has no open session: open it before moving notes.", config.name))
        return session

    def _nm_cash_method(self, session):
        cash_pm = session._nm_cash_payment_method()
        if not cash_pm:
            raise UserError(_("There is no cash payment method for this PoS Session"))
        return cash_pm

    def _nm_transit_account(self, line):
        """Counterpart account of a statement line of the transfer."""
        return (line.move_id.line_ids.account_id - line.journal_id.default_account_id)[:1]

    def _nm_post_note_moves(self, session, sign, origin='transfer'):
        """Note moves of the transfer in ``session``: its notes, quantity
        times ``sign``."""
        self.ensure_one()
        self.env['pos.nm.note.move'].sudo().create([{
            'session_id': session.id,
            'currency_id': self.currency_id.id,
            'value': value,
            'quantity': sign * quantity,
            'origin': origin,
            'transfer_id': self.id,
        } for value, quantity in self._nm_note_quantities()])

    def _nm_check_notes(self, session, notes):
        """Notes sent by denomination, when the sending counter tracks the
        notes of the currency: checked like the grids of the exchange popup
        (a shortfall of the stock is not refused). Without a grid from the
        back office, the notes proposed from the stock when they make up the
        amount exactly.

        :return: {key: quantity}, or False when the notes are not tracked
        """
        self.ensure_one()
        config = session.config_id
        currency = self.currency_id
        if currency not in config._nm_note_currencies():
            return False
        Exchange = self.env['pos.nm.exchange']
        if notes is None and not self.env.context.get('nm_transfer_from_ui'):
            proposal = Exchange._nm_propose_notes(currency, self.amount, Exchange._nm_note_rows(session, currency))
            if proposal['exact'] and not proposal['shortfall']:
                notes = {row['key']: row['proposed'] for row in proposal['rows']}
        grid = Exchange._nm_note_grid(config, currency, self.amount, notes, received=False, transfer=True)
        return {key: quantity for key, (_value, quantity) in grid.items()}

    # ------------------------------------------------------------------
    # Send, receive, cancel
    # ------------------------------------------------------------------

    def _nm_send(self, session=None, notes=None):
        """Send the notes from the open session of the sending counter: cash
        out on the transit account of the office, notes out of the stock."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("The note transfer %s was already sent.", self.name))
        self._nm_check_counters()
        session = self._nm_open_session(self.config_from_id, session)
        account = self.office_id.transit_account_id
        if not account:
            raise UserError(_(
                "Set the Notes in Transit Account of the exchange office %s before transferring notes.",
                self.office_id.name))
        currency = self.currency_id
        if currency.compare_amounts(self.amount, 0.0) <= 0:
            raise UserError(_("The amount of a note transfer must be positive."))
        cash_pm = self._nm_cash_method(session)
        available = session._nm_expected_cash(currency)
        if currency.compare_amounts(self.amount, available) > 0:
            raise UserError(_("The drawer of %(currency)s holds %(balance)s: %(amount)s cannot be sent.",
                              currency=currency.name, balance=currency.format(available),
                              amount=currency.format(self.amount)))
        notes = self._nm_check_notes(session, notes if notes is not None else self.notes or None)
        main = session.currency_id
        value = self.amount if currency == main else main.round(currency._convert(
            self.amount, main, session.company_id, fields.Date.context_today(self)))
        if main.is_zero(value):
            # Nothing would be booked on the transit account for notes that
            # are in transit: refused before the number is drawn.
            raise UserError(_("The amount %(amount)s is too small to be transferred: its value in %(main)s "
                              "rounds to zero.", amount=currency.format(self.amount), main=main.name))
        name = self.env['ir.sequence'].next_by_code('pos.nm.exchange.transfer') or '/'
        self.write({'name': name, 'value': value, 'notes': notes or False})
        line = self.env['pos.nm.exchange']._nm_post_line(
            cash_pm, session, -value, account,
            _('%(name)s: notes sent to %(counter)s', name=name, counter=self.config_to_id.name),
            self.env.user.partner_id, currency, self.amount)
        self.write({
            'state': 'sent',
            'session_from_id': session.id,
            'statement_line_from_id': line.id,
            'sent_date': fields.Datetime.now(),
            'sent_user_id': self.env.uid,
        })
        if notes:
            self._nm_post_note_moves(session, -1)
        message = _("Notes sent by %(user)s: %(amount)s to %(counter)s.", user=self.env.user.name,
                    amount=currency.format(self.amount), counter=self.config_to_id.name)
        self.message_post(body=message)
        session.message_post(body=_("Note transfer %(name)s: %(amount)s sent to %(counter)s.", name=name,
                                    amount=currency.format(self.amount), counter=self.config_to_id.name))

    def _nm_check_received_notes(self, session, notes):
        """Notes received by denomination, when the receiving counter tracks
        the notes of the currency and the sending one did not count them:
        checked like the grids of the exchange popup. Without a grid from
        the back office, a breakdown of the amount with the coins and notes
        of the counter, the largest first.

        :return: {key: quantity}, or False when the notes sent were counted
            or the receiving counter does not track them
        """
        self.ensure_one()
        config = session.config_id
        currency = self.currency_id
        if self.notes or currency not in config._nm_note_currencies():
            return False
        Exchange = self.env['pos.nm.exchange']
        if notes is None and not self.env.context.get('nm_transfer_from_ui'):
            rows = [dict(row, stock=0) for row in Exchange._nm_note_rows(session, currency)]
            proposal = Exchange._nm_propose_notes(currency, self.amount, rows)
            if proposal['exact']:
                notes = {row['key']: row['proposed'] for row in proposal['rows']}
        grid = Exchange._nm_note_grid(config, currency, self.amount, notes, received=True, transfer=True)
        return {key: quantity for key, (_value, quantity) in grid.items()}

    def _nm_receive(self, session=None, notes=None):
        """Receive the notes in the open session of the receiving counter:
        cash in of the value sent, notes into the stock when the receiving
        counter tracks them (those counted by the sending counter, else
        those counted at receiving: ``notes``)."""
        self.ensure_one()
        if self.state != 'sent' or not self.statement_line_from_id:
            raise UserError(_("The note transfer %s is not in transit.", self.name))
        config = self.config_to_id
        session = self._nm_open_session(config, session)
        currency = self.currency_id
        if currency not in config._nm_exchange_currencies():
            raise UserError(_("The counter %(config)s does not take %(currency)s in cash.",
                              config=config.name, currency=currency.name))
        received_notes = self._nm_check_received_notes(session, notes)
        cash_pm = self._nm_cash_method(session)
        account = self._nm_transit_account(self.statement_line_from_id) or self.office_id.transit_account_id
        line = self.env['pos.nm.exchange']._nm_post_line(
            cash_pm, session, self.value, account,
            _('%(name)s: notes received from %(counter)s', name=self.name, counter=self.config_from_id.name),
            self.env.user.partner_id, currency, self.amount)
        values = {
            'state': 'received',
            'session_to_id': session.id,
            'statement_line_to_id': line.id,
            'received_date': fields.Datetime.now(),
            'received_user_id': self.env.uid,
        }
        if received_notes:
            values['notes'] = received_notes
        self.write(values)
        if self.notes and currency in config._nm_note_currencies():
            self._nm_post_note_moves(session, 1)
        self.message_post(body=_("Notes received by %(user)s at %(counter)s.", user=self.env.user.name,
                                 counter=config.name))
        session.message_post(body=_("Note transfer %(name)s: %(amount)s received from %(counter)s.",
                                    name=self.name, amount=currency.format(self.amount),
                                    counter=self.config_from_id.name))

    def _nm_cancel(self):
        """Cancel a draft, or a transfer in transit while its sending
        session is open: cash in of the value sent on that session, the
        notes back in its stock."""
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError(_("The note transfer %s is already cancelled.", self.name))
        if self.state == 'received':
            raise UserError(_("The note transfer %s was received: it cannot be cancelled. Transfer the notes "
                              "back instead.", self.name))
        values = {'state': 'cancelled', 'cancel_date': fields.Datetime.now(), 'cancel_user_id': self.env.uid}
        if self.state == 'sent':
            session = self.session_from_id
            if not self.statement_line_from_id:
                raise UserError(_("The note transfer %s is not in transit.", self.name))
            if session.state not in OPEN_SESSION_STATES:
                raise UserError(_(
                    "The note transfer %(name)s was sent from the closed session %(session)s: it can only be "
                    "cancelled while that session is open. Receive it and transfer the notes back instead.",
                    name=self.name, session=session.name))
            cash_pm = self._nm_cash_method(session)
            line = self.env['pos.nm.exchange']._nm_post_line(
                cash_pm, session, self.value, self._nm_transit_account(self.statement_line_from_id),
                _('%(name)s cancelled: notes back from transit', name=self.name),
                self.env.user.partner_id, self.currency_id, self.amount)
            values['statement_line_cancel_id'] = line.id
            if self.note_move_ids:
                self._nm_post_note_moves(session, 1, origin='cancel')
            session.message_post(body=_("Note transfer %s cancelled.", self.name))
        self.write(values)
        self.message_post(body=_("Note transfer cancelled by %s.", self.env.user.name))

    def _nm_check_manager(self):
        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise AccessError(_("Only a Point of Sale manager can send or receive notes from the back office."))

    def action_send(self):
        """Back office: send the drafts from the open session of their
        sending counter (Point of Sale managers)."""
        self._nm_check_manager()
        self.check_access('write')
        for transfer in self.sudo():
            transfer._nm_send()
        return True

    def action_receive(self):
        """Back office: receive the transfers in transit in the open session
        of their receiving counter (Point of Sale managers)."""
        self._nm_check_manager()
        self.check_access('write')
        for transfer in self.sudo():
            transfer._nm_receive()
        return True

    def action_cancel(self):
        """Cancel the transfers: Point of Sale managers, or the cashier who
        sent a transfer still in transit."""
        self.check_access('read')
        if not self.env.user.has_group('point_of_sale.group_pos_manager') \
                and any(t.state != 'sent' or t.sent_user_id != self.env.user for t in self):
            raise AccessError(_("Only a Point of Sale manager, or the cashier who sent them while they are in "
                                "transit, can cancel a note transfer."))
        for transfer in self.sudo():
            transfer._nm_cancel()
        return True

    def action_view_statement_lines(self):
        self.ensure_one()
        lines = self.statement_line_from_id | self.statement_line_to_id | self.statement_line_cancel_id
        return {
            'name': _('Statement Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', lines.ids)],
        }

    def action_view_note_moves(self):
        self.ensure_one()
        return {
            'name': _('Note Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.nm.note.move',
            'view_mode': 'list',
            'domain': [('transfer_id', '=', self.id)],
        }

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    def _nm_transfer_data(self):
        """Data of the transfer for the register and its transfer slip."""
        self.ensure_one()
        Exchange = self.env['pos.nm.exchange']
        received = self.state == 'received'
        user = self.received_user_id if received else self.sent_user_id
        return {
            'id': self.id,
            'name': self.name,
            'config_from': self.config_from_id.name,
            'config_to': self.config_to_id.name,
            'currency': self.currency_id.name,
            'currency_id': self.currency_id.id,
            'amount': self.amount,
            'amount_formatted': self.currency_id.format(self.amount),
            'notes_label': self.notes_label or '',
            'note': self.note or '',
            'state': self.state,
            'state_label': dict(self._fields['state']._description_selection(self.env))[self.state],
            'sent_date': Exchange._nm_local_datetime(self.sent_date),
            'received_date': Exchange._nm_local_datetime(self.received_date),
            'date': Exchange._nm_local_datetime(self.received_date if received else self.sent_date),
            'cashier_name': user.name or '',
        }

    @api.model
    def _nm_register_session(self, session_id):
        """Open session of the register, at a counter whose exchange counter
        is enabled and readable by the cashier."""
        session = self.env['pos.session'].browse(int(session_id)).exists()
        if not session or session.state not in OPEN_SESSION_STATES:
            raise UserError(_("The session must be open to transfer notes."))
        self.env['pos.nm.exchange']._nm_counter_config(session.config_id.id)
        session.check_access('read')
        return session

    @api.model
    def get_transfer_targets(self, config_id):
        """Register: counters of the office to which the notes can be sent,
        and the currencies of the counter with, for those whose notes are
        tracked, the coins and notes and their stock in the drawer."""
        config = self.env['pos.nm.exchange']._nm_counter_config(config_id).sudo()
        office = config.nm_exchange_office_id
        targets = [{
            'id': target.id,
            'name': target.name,
            'session_open': target.current_session_state in OPEN_SESSION_STATES,
        } for target in (office.config_ids - config).filtered('nm_exchange_enabled').sorted('name')] if office else []
        session = config.current_session_id
        if session.state not in OPEN_SESSION_STATES:
            session = self.env['pos.session']
        tracked = config._nm_note_currencies()
        currencies = []
        for currency in config._nm_exchange_currencies():
            rows = []
            if currency in tracked:
                rows = self.env['pos.nm.exchange']._nm_note_rows(session, currency) if session else [{
                    'key': _nm_note_key(bill.value), 'value': bill.value, 'label': currency.format(bill.value),
                    'stock': 0,
                } for bill in config._nm_note_bills(currency)]
            currencies.append({
                'id': currency.id,
                'name': currency.name,
                'symbol': currency.symbol,
                'decimal_places': currency.decimal_places,
                'tracked': currency in tracked,
                'rows': rows,
            })
        return {'targets': targets, 'currencies': currencies}

    @api.model
    def send_from_ui(self, session_id, config_to_id, currency_id, amount, *, notes=None, note=None, uuid=None):
        """Register: create the transfer and send the notes from the open
        session of the register.

        :param notes: notes sent by denomination ({value key: quantity}),
            required when the counter tracks the notes of the currency: they
            must add up to the amount
        :param uuid: identifier of the transfer generated by the register:
            when it was already recorded (the response was lost and the
            cashier confirms again), nothing is recorded twice
        :return: the data of the transfer (``_nm_transfer_data``)
        """
        self.env['pos.nm.exchange']._nm_check_pos_user()
        if uuid:
            recorded = self.sudo().search([('uuid', '=', uuid), ('session_from_id', '=', int(session_id))], limit=1)
            if recorded:
                if recorded.config_to_id.id != int(config_to_id) or recorded.currency_id.id != int(currency_id) \
                        or recorded.currency_id.compare_amounts(recorded.amount, float(amount)):
                    raise UserError(_("Another note transfer was already recorded with this register identifier."))
                return recorded._nm_transfer_data()
        session = self._nm_register_session(session_id)
        config = session.config_id
        office = config.nm_exchange_office_id
        if not office:
            raise UserError(_("The counter %s does not belong to an exchange office.", config.name))
        config_to = self.env['pos.config'].sudo().browse(int(config_to_id)).exists()
        currency = self.env['res.currency'].browse(int(currency_id)).exists()
        if not config_to or not currency:
            raise UserError(_("Unknown point of sale or currency."))
        # Received at its register only: a counter whose exchange counter
        # is disabled is not offered (the back office still records them).
        if not config_to.nm_exchange_enabled:
            raise UserError(_("The currency exchange counter is disabled on %s.", config_to.name))
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise UserError(_("The amount of a note transfer must be positive."))
        if currency.compare_amounts(amount, 0.0) <= 0:
            raise UserError(_("The amount of a note transfer must be positive."))
        transfer = self.sudo().with_context(mail_create_nosubscribe=True, mail_create_nolog=True).create({
            'office_id': office.id,
            'company_id': config.company_id.id,
            'config_from_id': config.id,
            'config_to_id': config_to.id,
            'currency_id': currency.id,
            'amount': amount,
            'note': note or False,
            'uuid': uuid or False,
        })
        transfer.with_context(nm_transfer_from_ui=True)._nm_send(session, notes)
        return transfer._nm_transfer_data()

    @api.model
    def get_incoming_transfers(self, config_id):
        """Register: transfers in transit to the counter, the oldest first.
        ``needs_notes``: the counter tracks the notes of the currency and the
        sending counter did not count them, the cashier counts them at
        receiving, in a grid of the coins and notes of ``rows``."""
        Exchange = self.env['pos.nm.exchange']
        config = Exchange._nm_counter_config(config_id).sudo()
        session = config.current_session_id
        if session.state not in OPEN_SESSION_STATES:
            session = self.env['pos.session']
        tracked = config._nm_note_currencies()
        transfers = []
        for transfer in self.sudo().search([('config_to_id', '=', config.id), ('state', '=', 'sent')],
                                           order='sent_date, id'):
            currency = transfer.currency_id
            needs_notes = not transfer.notes and currency in tracked
            rows = []
            if needs_notes:
                rows = Exchange._nm_note_rows(session, currency) if session else [{
                    'key': _nm_note_key(bill.value), 'value': bill.value, 'label': currency.format(bill.value),
                    'stock': 0,
                } for bill in config._nm_note_bills(currency)]
            transfers.append({
                'id': transfer.id,
                'name': transfer.name,
                'config_from': transfer.config_from_id.name,
                'currency': currency.name,
                'currency_id': currency.id,
                'amount': transfer.amount,
                'amount_formatted': currency.format(transfer.amount),
                'notes_label': transfer.notes_label or '',
                'sent_date': Exchange._nm_local_datetime(transfer.sent_date),
                'note': transfer.note or '',
                'needs_notes': needs_notes,
                'rows': rows,
            })
        return transfers

    @api.model
    def receive_from_ui(self, transfer_id, session_id, *, notes=None):
        """Register: receive a transfer in transit in the open session of the
        register. Received again in the same session (the response was
        lost), nothing is recorded twice.

        :param notes: notes received by denomination ({value key: quantity}),
            required when the counter tracks the notes of the currency and
            the sending counter did not count them: they must add up to the
            amount

        :return: the data of the transfer (``_nm_transfer_data``)
        """
        self.env['pos.nm.exchange']._nm_check_pos_user()
        session = self._nm_register_session(session_id)
        transfer = self.sudo().browse(int(transfer_id)).exists()
        if not transfer or transfer.config_to_id != session.config_id:
            raise UserError(_("This note transfer is not sent to this counter."))
        if transfer.state == 'received' and transfer.session_to_id == session:
            return transfer._nm_transfer_data()
        transfer.with_context(nm_transfer_from_ui=True)._nm_receive(session, notes)
        return transfer._nm_transfer_data()
