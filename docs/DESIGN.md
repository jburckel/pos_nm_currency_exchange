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
  that the amount handed back is the one quoted to the cashier (`amount_out`). The
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
  connection is requested again 5 s later while the inputs do not change. The receipt templates are QWeb views added to the templates the POS
  loads (`ir.ui.view._get_xml_ids_to_load`); the receipt body is shared with the
  PDF report of the operation.

## Settings

- Per currency, on `pos.nm.currency.setting`: Exchange Sell Margin (%), commission
  in percent, fixed commission, minimum commission, logged in the chatter.
- On the point of sale: counter enabled, commission income account (income types
  only), exchange licence number, customer required above, customer required for
  every operation, identity document required above, linked operations period
  (days).

## Identification

- Value compared to the thresholds: received value, plus with a linked period the
  done operations of the same customer over the last N x 24 h at every point of
  sale of the company (`_nm_linked_value`).
- Above the document threshold: customer and valid (not expired) identity document
  required. The document is frozen on the operation with the customer name. The
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
  PDF report on `pos.config`.

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
