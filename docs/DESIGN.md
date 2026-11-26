# Design notes

Version 20.0.2.0.0, on `pos_nm_multicurrencies` 20.0.2.1.0 or later (see the parent
module for the primitives it relies on: drawers per currency, cash rates and fixed
rates, coins and notes, payment and change rounding, Currency Position, deposits,
drawer revaluation, counts per cashier).

## Operation

- One record per operation (`pos.nm.exchange`, with `mail.thread`): session,
  cashier (name and `user_id`), customer and frozen customer name, currency and
  amount received, currency and amount handed back, received and handed values in
  the currency of the point of sale, rate (12 decimals) and its label, commission,
  rate margin, operation type (purchase, sale, cross), status (done, cancelled),
  register identifier (`uuid`), frozen copy of the identity document.
- Pricing (`_nm_quote`): the notes received are valued at the cash rate of the
  parent (`_nm_from_currency`: rate of Odoo x (1 + Cash Rate Margin), or the Fixed
  Rate); the notes handed back at the sell rate of the counter
  (`pos.config._nm_exchange_sell_rate`: rate of Odoo / (1 + Exchange Sell Margin),
  or the lower of the Fixed Rate and the Fixed Change Rate). The commission of the
  foreign currency (the handed one when both are foreign) is deducted from the
  received value, then the notes handed back are rounded once, down, to the
  Change Rounding of a foreign currency or the cash rounding of the point of sale
  (`rounding_method`) for its own currency, else the currency rounding. The
  commission is received value - handed value, so the remainder of the rounding
  stays in it and it is never below the configured one.
- Rate margin (`_nm_rate_margin`): market value of the notes received at the rate
  of Odoo - received value + handed value - market value of the notes handed back.
  It is what the drawer revaluation of the parent realizes at closing.
- Reverse quote (`_nm_reverse_amount_in`, RPC `get_reverse_quote`): smallest amount
  received, rounded up to the payment step of the received currency (Payment
  Rounding, else Change Rounding kept as rounding, cash rounding of the point of
  sale for its currency, else currency rounding), whose quote hands back at least
  the amount asked.
- Two statement lines on the cash journal of the session, like a cash in and a
  cash out of `pos_nm_multicurrencies`: the notes received (positive, in their
  currency, at the received value) and the notes handed back (negative, in their
  currency, at the handed value). Both lines take the commission income account of
  the point of sale as counterpart, so the commission is the net of that account.
  The lines carry the cashier as partner; they cannot be deleted
  (`account.bank.statement.line` unlink check).
- `create_from_ui` is the only way to create an operation (POS users have no
  create right; the method checks and creates with sudo). It checks the POS user,
  the session (open), the counter (enabled, commission account), the currencies,
  the identification rules (recomputed server side), the drawer of the currency
  handed back in every currency (closing control amount of the open session), and
  that the amount handed back is the one quoted to the cashier (`amount_out`). That
  last refusal is `NmQuoteChangedError` (a `UserError`) whose `context` carries
  `nm_exchange_error: 'nm_exchange_quote_changed'`, the amount sent and the amount
  quoted; the popup reads it from `error.data.context` (not from the translated
  message), requests a new quote of the same inputs at once and shows a warning,
  and the cashier confirms again (never automatically). The
  cashier is the user, or the employee logged in with `pos_hr` (checked against the
  employees of the point of sale). A second call with the same `uuid` returns the
  operation already recorded (lost connection), after `_nm_check_same_operation`:
  it is refused when the currencies, the amount received, the amount handed back
  or the customer differ from the operation recorded (the register freezes its
  inputs, the note included, until then, but the server does not trust it).
- References `EXC/YYYY/NNNNN` from a `no_gap` sequence.
- The register: entries "Currency Exchange", "Exchange Operations" and "Exchange
  Rates" in the burger menu. The exchange popup quotes through debounced RPCs
  (`get_quote`, `get_reverse_quote`), drops the stale answers, enables Confirm only
  for the quote of the amounts shown, and prints the receipt through the ticket
  printer. A `ConnectionLostError` is shown as a translated message (the server
  message `error.data.message` only for server errors); a quote lost with the
  connection is requested again 5 s later while the inputs do not change. The
  receipt templates are QWeb views added to the templates the POS
  loads (`ir.ui.view._get_xml_ids_to_load`); the receipt body is shared with the
  PDF report of the operation.

## Settings

- Per currency, on `pos.nm.currency.setting`: Exchange Sell Margin (%), commission
  in percent, fixed commission, minimum commission, logged in the chatter. A setting
  created without a sell margin starts from `nm_default_sell_margin(margin_percent)`
  (m when positive, -m / (1 + m/100) when negative: the same sell rate), the helper
  of the pre-migration; an onchange follows the Cash Rate Margin until the record is
  saved, a saved setting is never changed.
- On the point of sale: counter enabled, commission income account (income types
  only), exchange licence number, customer required above, customer required for
  every operation, identity document required above, linked operations period
  (days).

## Identification

- Value compared to the thresholds: received value, plus with a linked period the
  done operations of the same customer over the last N x 24 h at every point of
  sale of the company (`_nm_linked_value`).
- Above the document threshold: customer and valid (not expired) identity document
  required: type, number and expiry date, or *No expiry date*
  (`nm_id_document_no_expiry` / `id_document_no_expiry`) for a document without one.
  The expiry date and the box are a pair: one sent clears the other, the pair of the
  contact is kept only when neither is sent for the same document. The document is frozen on the operation with the customer name. The
  receipt prints the document type and the last 4 characters of its number.
- The register sends the document typed (`_nm_document_values`): the fields left
  empty keep the values of the contact when the document is the same (same type,
  number empty or equal), else only the nationality and the date of birth do.
- The document is written on the contact (`res.partner` fields, readable by POS
  managers only, not copied on duplicate) only when it differs from the one
  recorded, with a note in the chatter of the contact (masked number)
  (`_nm_save_customer_document`). The contact of an internal user (`share` false,
  archived users included through `active_test=False`) is written only when the
  cashier is a POS manager; otherwise the document stays on the operation alone.
  Portal and public users do not protect their contact: they are customers.
- Cashiers read the document of the selected customer through
  `get_customer_document(config_id, partner_id)`: sudo after an access check on the
  customer, refused unless the counter of that point of sale is enabled and has a
  document threshold, and partial: type, issuing country, expiry date and the last
  4 characters of the number (`number_masked`). Nationality and date of birth are
  not returned; the popup shows them empty.
- The popup shows the linked value (with the operations of the customer) only when
  it exceeds a threshold (`get_quote` replaces it by the value of the operation
  otherwise): the exchanges of a customer are not shown to the cashier without
  reason.

## Cancellation

- `action_cancel` (POS managers): only while the session is open and when the
  drawer holds the notes received. Two statement lines exactly opposite to the
  original ones (same amounts in both currencies, same counterpart account), status
  `cancelled`, cancel date and user, message on the session and the operation.
- Cancelled operations are left out of the counts, commissions and rate margins of
  the session button, the closing popup, the Sales Details report and the point of
  sale; the closing popup and the reports name them apart.

## Reporting

- Closing popup: the operations appear in the cash moves of each currency (parent
  module) and a "Currency Exchange" block gives the count, the operations, the
  commissions, the rate margin and the cancelled operations.
- Currency Position: unchanged (the operations are statement lines of the drawers).
- Session form: stat button with the commissions and the number of operations.
- Sales Details: "Currency Exchange" block; from sessions, the operations of the
  sessions; by period, the operations dated in the period on the selected points of
  sale; totals per currency of the points of sale.
- Back office: list, form, pivot and search of `pos.nm.exchange` under Point of
  Sale > Orders > Currency Exchanges; PDF receipt and e-mail (mail template).
- Exchange Register (Point of Sale > Reporting): list in reference order with the
  identity documents (Excel through Export) and PDF per period
  (`pos.nm.exchange.register.wizard`, A4 landscape, totals per currency).
- Rate board (`pos.config._nm_rate_board`): register popup, receipt printer and
  PDF report on `pos.config`. The typical amount (`_nm_board_amount`) is the power of
  10 nearest to 100 units of the currency of the point of sale, rounded to the
  nearest common multiple of its payment step (`_nm_payment_step`) and change step
  (`pos.nm.exchange._nm_change_step`), at least one step: the board row is exactly
  what an operation of that amount records.

## Security model

- `pos.nm.exchange`: POS users read, POS managers read and write (the note only:
  `write` refuses every other field), nobody creates through the ORM except
  `create_from_ui`, nobody deletes. Multi-company record rule on `company_id`.
- Identity fields of `res.partner` and `pos.nm.exchange`: `groups` POS managers.
- Menus Currency Exchanges and Exchange Register, register wizard: POS managers.
- `pos.config.write`: the POS users write the point of sale from the register, but a
  value of an `nm_exchange_*` field (counter enabled, commission account, thresholds,
  linked period, licence) is refused unless the user is a POS manager or a system
  administrator (or sudo).

## Migration 20.0.2.0.0

- Parent version: `pre_init_hook` (installation) and the pre-migrate script
  (upgrade) call `_nm_check_parent_version`, which refuses `pos_nm_multicurrencies`
  older than 20.0.2.1.0 (the register imports its coin helpers and would not load).
- pre: Exchange Sell Margin = Cash Rate Margin (-m / (1 + m/100) when negative: same sell rate); user of the
  operations = their creator.
- post: status done, rate recomputed, rate margin at the rate of Odoo of the day of
  each operation, customer name, linked value, reference sequence `no_gap`. A done
  operation whose statement line (received or handed back) was deleted under
  20.0.1.x is logged as a warning and gets a message in its chatter, once (an
  existing message is looked up), telling to correct the drawer with a cash move.
  The scripts are idempotent (empty values filled, rate recomputed from the
  amounts): they can run twice.

## Exchange office (20.0.3.0.0)

- `pos.nm.exchange.office`: company, address, licence, compliance officer,
  counters (`pos.config.nm_exchange_office_id`, same currency as the
  company), reference counter, rules (thresholds, customer always, linked
  period), board token and refresh. `pos.config._nm_rules()` returns the
  rules of the office, else of the point of sale (`RULE_FIELDS`): every
  check reads it, never the fields directly.
- *Apply Rates to the Counters* writes `SYNCED_SETTING_FIELDS` of each
  setting of the reference counter on the other counters (create when
  missing and the cash method accepts the currency), so the chatter of the
  settings logs it (`_NM_LOGGED_FIELDS`).

## Compliance

- `_nm_identification` adds `origin_required` and `review_required`.
  Origin of funds above its threshold is required like the document
  (customer, origin, details for Other), checked server side
  (`_nm_identification_error`). The register sends `declaration`
  (`funds_origin`, `funds_origin_note`, `purpose`, `pep`), cleaned by
  `_nm_declaration_values`.
- Review (threshold or PEP declared): `compliance_state = 'to_review'`,
  `review_reason`, activity to the compliance officer of the office
  (`mail.activity.mixin`). Never refused at the counter.
- `write`: POS managers change `note`, `compliance_state`,
  `compliance_note` only (`MANAGER_FIELDS`).

## Register hash

- `_nm_hash_register` (after the statement lines, in `create_from_ui`):
  advisory transaction lock per company (`HASH_LOCK`), previous hash =
  last hashed operation of the company by id, SHA-256 of
  `_nm_hash_string` (amounts with the decimals of their currency, rate with
  12). `cancel_hash` chains the cancellation to the operation hash.
- A hashed operation refuses any change of `_nm_hashed_fields`, sudo
  included; the database itself is checked by
  `_nm_check_register_integrity` (first broken operation and why).
- `pos.nm.exchange.register.closing._nm_close`: period over, sessions of
  its operations closed, no overlap with a closing of the same office or
  of the company, integrity intact; PDF rendered with `raw` and attached.
  `_nm_cancel` refuses an operation inside a closing.

## Rate board page

- `controllers/rate_board.py`: public routes, token compared with
  `consteq`, `sudo().with_company()`. HTML page `rate_board_page` without
  Odoo assets (`static/board/`, outside `static/src` so that the POS
  bundle does not load it) and a JSON route for the refresh.
- Customer display: `_get_customer_display_data` adds `nm_rate_board_url`
  when the option is ticked; `static/src/customer_display_board/` (removed
  from `_assets_pos`, added to `point_of_sale.customer_display_assets`)
  replaces the idle logo and *Welcome* with an iframe of the board.

## Note stock

- Foreign cash currencies only: POS Multi-Currency Cash counts them by
  denomination at opening and closing (`opening_details` / `closing_details`
  of `pos.session.currency.detail`, `{key: quantity}`); the currency of the
  point of sale has no such count. A currency is tracked at a point of sale
  when `nm_exchange_track_notes` is ticked and it has coins and notes there
  (`pos.bill` of that currency, with the load domain of the register:
  `default_bill_ids` or no point of sale): `pos.config._nm_note_currencies`,
  sent to the register as `_nm_note_currency_ids`.
- Key of a denomination: `_nm_note_key(value)` (`"50"`, `"0.5"`), the
  `String(bill.value)` of the register. Keys received are parsed with
  `float()` and normalized, never compared as raw strings.
- `pos.nm.note.move`: session, currency, value, signed quantity, origin
  (exchange, cancellation), operation. Created with sudo by
  `create_from_ui` (after the statement lines, not on a replay) and
  `_nm_cancel` (the opposite of the exchange moves); `write` and `unlink`
  refused outside sudo; POS users and managers read only.
- `pos.session._nm_note_stock(currency)`: opening count + one read_group of
  the moves, per denomination (and any value counted or moved that is no
  longer a coin or note), without the closing control computation. The
  stock follows the exchange operations only: cash sales and cash moves in
  a foreign currency change the drawer without denominations, so a
  shortfall is a warning and the next count corrects the stock.
- Quote: `notes_in` (rows with their stock) and `notes_out` (rows with the
  `proposed` quantity, `exact`, `shortfall`, `error`) while a session is
  open and the side is tracked, else None. Proposal: the largest first
  within the stock, then a bounded search within the stock, then whatever
  the stock (shortfall naming the missing notes), else the greedy
  breakdown below the amount with an error.
- `create_from_ui(notes_in=, notes_out=)`: for a tracked side the grid is
  required and checked after the drawer, before the number is drawn
  (known denominations, whole quantities from 0, total equal to the amount
  with `compare_amounts`).
- Register RPC `get_note_stock(config_id)`; closing control data: the
  `multicurrency_details` entries of the tracked currencies get
  `nm_expected_notes` (`{key: stock}`).
- Report `pos.nm.note.stock`: SQL view, one row per session, currency and
  value from the opening and closing counts (`jsonb_each_text`) and the
  moves; In and Out are the positive and negative moves (a cancellation
  counts in the opposite column); Difference = closing - stock, only when
  the closing was counted by denomination. Multi-company rule, POS
  managers.

## Note transfers

- `pos.nm.exchange.transfer` (*Note Transfer*, `mail.thread`): office, from
  and to counters (both of the office, different, in the currency of the
  office, both taking the currency of the transfer in cash:
  `_nm_check_counters`, a constraint checked again when sending), currency,
  amount (> 0), value in the currency of the company, state draft / sent
  (*In Transit*) / received / cancelled, sessions, the three statement
  lines, dates and users, note, `notes` (Json `{key: quantity}`), note
  moves, `uuid` (unique).
- Reference `TRF/YYYY/NNNNN` (`no_gap`) drawn by `_nm_send` after every
  check: a draft keeps `/`, a refused sending draws no number.
- `_nm_send`: open session of the sending counter, transit account of the
  office (`transit_account_id`, current assets), drawer of the currency
  (`_nm_expected_cash`, "cannot be sent"), notes grid when the currency is
  tracked at the sending counter (`pos.nm.exchange._nm_note_grid(...,
  transfer=True)`: same rules as the exchange grids, a stock shortfall is
  not refused). Value frozen: the amount in the currency of the point of
  sale, else the amount at the rate of Odoo of the day, like the cash moves
  of POS Multi-Currency Cash; a value rounding to zero is refused ("too
  small to be transferred") before the number is drawn. Cash out through
  `pos.nm.exchange._nm_post_line` (an `@api.model` helper shared with the
  operations: foreign line and `cash_moves_amount` of the detail, signed
  with `math.copysign` like core, so a line worth 0 keeps its sign), label
  `TRF/...: notes sent to <counter>`; note moves `-qty`, origin
  `transfer`. From the back office (*Send*, POS managers) without a grid,
  the notes proposed from the stock are sent when they make up the amount
  within the stock, else the register is asked for.
- `_nm_receive`: open session of the receiving counter, cash in of the same
  value and amount on the counterpart account of the sending line; note
  moves `+qty` when the receiving counter tracks the currency: the notes
  sent, or, when the sending counter did not count them, the notes counted
  at receiving (`_nm_check_received_notes`: grid `notes` of
  `receive_from_ui`, `_nm_note_grid(..., received=True, transfer=True)`;
  from the back office a breakdown of the amount, the largest first),
  written to `notes`. The amount received is the amount sent: a difference
  is found by the closing count.
- `_nm_cancel`: a draft is cancelled as is; a transfer in transit only
  while its sending session is open (cash in of the value on that session,
  opposite note moves, origin `cancel`); a received transfer never. POS
  managers, or the cashier who sent it while it is in transit.
- `create` / `write` (`_nm_check_system_fields`): outside sudo, the fields
  written by the transfer itself (`TRANSFER_SYSTEM_FIELDS`: name, state,
  value, notes, uuid, sessions, lines, dates and users, note moves) are
  refused whatever the state (a new transfer may carry `name='/'` and
  `state='draft'`); a transfer that is not a draft refuses every field but
  `note`; only drafts are deleted. Receiving and cancelling also require
  the sending line. Its statement lines cannot be
  deleted (`account.bank.statement.line._unlink_except_exchange_leg`).
- Register RPCs (POS user, `_nm_counter_config`, sudo after the checks):
  `get_transfer_targets(config_id)` -> `{targets: [{id, name,
  session_open}] (the enabled counters only), currencies: [{id, name,
  symbol, decimal_places, tracked,
  rows: [{key, value, label, stock}]}]}`; `send_from_ui(session_id,
  config_to_id, currency_id, amount, *, notes, note, uuid)` (a replay of
  the uuid in the same session returns the transfer recorded; a disabled
  receiving counter is refused); `get_incoming_transfers(config_id)` ->
  `[{id, name, config_from, currency, currency_id, amount,
  amount_formatted, notes_label, sent_date, note, needs_notes, rows}]`;
  `receive_from_ui(transfer_id, session_id, *, notes)` (received again in the same
  session: returned as is). Both return `_nm_transfer_data()`, also the
  data of the transfer slip `pos_exchange_transfer_receipt`.
- `pos.config._nm_transfer_enabled()` (`_nm_transfer_enabled` in the data
  of the register): counter enabled and another enabled counter in its
  office. A refused receipt reloads the list of the register.
- Office: *Transfers* smart button and the *Drawers* page,
  `drawers_html` rendered from `_nm_drawers()` (template
  `exchange_office_drawers`): per counter with an open session the expected
  cash of each currency (one closing control computation per session:
  `_nm_expected_cash(currency, data)`), the operations of the day (time
  zone of the user) and their commissions; the transfers in transit per
  currency and their value, which is the balance of the transit account.

