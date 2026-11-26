# Changelog

All notable changes to the POS Currency Exchange module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [20.0.2.0.0] - 2026-11-25

Requires `pos_nm_multicurrencies` 20.0.2.1.0 or later (the installation and
the upgrade are refused otherwise). Upgrade with
`-u pos_nm_currency_exchange`: the migration fills the new fields of the
existing operations (see *Upgrade* below). Close the sessions, or reload
every register, after the upgrade: a register still running 20.0.1.x
cannot record operations.

### Upgrade: what changes for your counter
- **The notes handed back are priced at a sell rate, in favour of the
  shop.** Before, they used the marked-up cash rate of the notes received,
  so with a Cash Rate Margin the counter sold foreign notes *below* the
  market (margin 10 %, rate 2.0: 100 received in the POS currency gave
  213 EUR worth 106.50; now 176 EUR worth 88). The new *Exchange Sell
  Margin (%)* of each currency is set to its Cash Rate Margin on upgrade;
  a negative Cash Rate Margin, which already sold the notes above the
  rate of Odoo, becomes the sell margin that keeps that sell rate (-2 %
  becomes 2.04 %): check it in *Cash Currencies*. A currency added after
  the upgrade starts from its Cash Rate Margin the same way (and follows
  it in the form until it is saved), instead of selling its notes at the
  rate of Odoo. With fixed rates, the
  notes are handed back at the lower of the Fixed Rate and the Fixed
  Change Rate.
- **Operations can no longer be deleted or edited** (only their note, by a
  manager). A mistake is undone with the new *Cancel Operation* while the
  session is open. The two statement lines of an operation cannot be
  deleted either.
- **POS users (cashiers) only read the operations**: they are recorded from
  the register only. The *Currency Exchanges* and *Exchange Register* menus
  are for POS Administrators.
- **References are gapless** (`EXC/YYYY/NNNNN`): the sequence is switched to
  "no gap" on upgrade.
- **The drawer is checked for every currency handed back, the currency of
  the point of sale included**, with the amount of the closing control
  (opening, cash sales and change of the session, cash moves, exchanges).
  An operation the drawer cannot pay is refused.
- **Notes handed back in the currency of the point of sale are rounded down
  to its cash rounding** (*Total Rounding* of the point of sale) when set;
  the remainder stays in the commission.

### Added
- **Exchange Sell Margin (%)** per currency (*Cash Currencies*, group
  *Currency Exchange*), logged in the chatter like the rates.
- **Rate Margin** of every operation: what the rates earn against the rates
  of Odoo of the day (commission + rate margin = income of the operation,
  realized at the deposit or revaluation of the notes). Shown on the
  operation, in the list, the pivot, the closing popup and the Sales
  Details report. **Rate Applied** shows the rate as "1 USD = 119.33 XPF".
- **Reverse quote**: type the amount the customer wants in *Handed back*;
  the amount to receive is computed, rounded up to the coins of the
  received currency.
- **In the drawer** line in the popup: balance of the drawer of the currency
  handed back; an operation above it is refused before *Confirm*.
- **Cancel Operation** (POS Administrators), while the session is open and
  the drawer still holds the notes received: two statement lines exactly
  opposite to the original ones, drawers and commission account back to
  their state; status *Cancelled*, date and user, message on the session.
  Cancelled operations are left out of the counts, commissions, closing
  summary and reports, and listed apart.
- **Customer identification**: *Customer required for every operation*,
  *Identity document required above* and *Linked operations period (days)*
  (the operations of the same customer over that period are added to the
  thresholds, at every point of sale of the company). Identity document of
  the customer (type, number, issuing country, expiry date or *No expiry
  date* for an older document without one, nationality, date of birth)
  entered in the popup, stored on the contact (new tab
  *Identity Document*, POS Administrators only) and copied on the
  operation with the customer name; expired documents are refused.
- **Receipt**: header and footer of the point of sale, *Exchange licence
  number* (new setting), operation type (purchase, sale or cross exchange),
  date and time with seconds, masked document number; reprint marked
  *COPY*, cancelled operations marked *CANCELLED*.
- **Register menu**: *Exchange Operations* (operations of the session,
  *Reprint*) and *Exchange Rates* (rate board, *Print*). The typical
  amount of the rate board (register and PDF) is a multiple of the Payment
  Rounding and of the Change Rounding of the currency (99 CHF with 3 CHF
  coins): its figures are those of the quote and the counter takes them
  as they are.
- **Back office**: *Print* (PDF *Exchange Receipt*) and *Send by E-mail*
  on the operation, chatter on the operations; *Operation Type* column,
  filters and grouping; *Print Exchange Rates* in the settings and the
  *Print* menu of the point of sale (PDF *Exchange Rates*).
- **Exchange Register** (*Point of Sale -> Reporting*, POS
  Administrators): every operation in reference order, cancelled ones
  included, with the identity documents; Excel through *Export*, PDF of a
  period with *Print Register* (totals per currency).
- Messages instead of the popup when the counter cannot work (no foreign
  cash currency, no commission account).
- Store page: screenshot of the rate board in PDF.

### Changed
- The cashier of an operation is decided by the server: the user, or the
  employee logged in at the register with the Employees module. The
  statement lines carry the cashier as partner, no longer the customer.
- The commission account must be an income account.
- The "too small" refusal also shows in the quote.
- An operation is refused when its quote changed between the popup and the
  server (rates, sell margin or commission changed meanwhile): the popup
  requests the new quote at once and asks the cashier to check it with the
  customer before confirming again; it is never confirmed on its own.
- *Sales Details* run for a period lists the operations of that period on
  the selected points of sale, open sessions included; commissions and
  rate margins are totalled per currency.
- Session form: the button shows the commissions and "Exchanges: N".
- The closing popup shows the exchange block whenever the session has
  operations, with the rate margin and the cancelled operations.

### Fixed
- The commission could fall below the minimum, or become negative, once the
  notes handed back were rounded: they are now rounded down once and the
  remainder always stays in the commission.
- Rates of currencies such as VND or IDR were stored as 0 or 0.000036: the
  rate is stored with 12 decimals (recomputed on upgrade).
- Changing an amount while a quote was on its way could confirm the old
  quote; *Confirm* waits for the quote of the amounts shown.
- Confirming again after a lost connection could record the operation
  twice; the register now sends an identifier and the server records it
  once. After a lost connection the popup freezes the amounts, currencies,
  customer, document and note, keeps *Confirm* enabled to confirm again, and the server
  refuses an identifier already recorded with other amounts.
- *Discard* and *Escape* closed the popup while the operation was being
  recorded.
- The drawer opening was logged twice; a failed drawer opening no longer
  prevents the receipt.
- The amount to receive of a reverse quote now follows the coins used by
  the warning of the popup (Payment Rounding, else Change Rounding kept as
  rounding).
- Reverse quote: the *Handed back* field could keep the amount typed
  instead of the amount actually handed back; the quote summary now shows
  a *Handed back* line, and *Swap* asks for the amount typed in the other
  currency, not the one rounded for the first.
- *Exchange Rates* and *Exchange Operations* show an error in the popup
  when they cannot be loaded, instead of a connection error dialog. A lost
  connection is explained in the language of the user, in these popups and
  for the quote and the identity document of the exchange popup; a quote
  lost with the connection is requested again a few seconds later.
- The count lines of the closing popup, the Sales Details and the Exchange
  Register read "1 operation" and "1 cancelled operation" in the singular.
- The expiry date of a refused document, the amount placeholders and the
  commission rule of the rate board follow the language of the user.

### Security
- Access rights: POS users read the operations, POS Administrators edit the
  note only, nobody deletes; multi-company record rule on the operations.
- The register cannot record an operation for an employee who is not
  allowed on the point of sale, nor for a customer the cashier cannot
  read.
- Only POS Administrators change the settings of the counter (thresholds,
  linked operations period, commission account, licence), also through
  RPC.
- The register reads the identity document of a customer only at a point
  of sale whose counter asks for documents, and only its type, issuing
  country, expiry date and the last 4 characters of its number. A
  document changed at the register is saved and logged on the contact;
  the contact of an internal user, even archived, is changed by a POS
  Administrator only (a customer with a portal account is a customer).
- The quote shows the exchanges of a customer over the linked operations
  period only when they make the customer or the document required.
- The identity fields of contacts and operations are restricted to POS
  Administrators; cashiers see them only in the popup.
- The identity document of a contact is not copied when the contact is
  duplicated.

### Upgrade
- *Exchange Sell Margin* of the existing currencies = their Cash Rate
  Margin; *User* of the existing operations = their creator; status
  *Done*; rate recomputed with full precision; *Rate Margin* computed at
  the rate of Odoo of the day of each operation (the operations made
  before show the loss of the old pricing on the notes handed back);
  *Customer Name* filled from the contact; reference sequence switched to
  "no gap". Operations one of whose statement lines was deleted with
  20.0.1.x are reported in the server log and by a message on the
  operation (correct the drawer with a cash move). The migration can run
  twice safely.

## [20.0.1.1.0] - 2026-09-29

Requires `pos_nm_multicurrencies` 20.0.2.1.0.

### Added
- **Warning on amounts the coins cannot make up**: the exchange popup warns
  when the amount received in a foreign currency is not a multiple of its
  Payment Rounding, else of its Change Rounding when its *Remainder of the
  Change* is *Kept as rounding* (1,106 XPF with 5 XPF coins). The operation
  stays possible.

### Fixed
- The changes of the *Remainder of the Change* of a currency are logged in
  the chatter with this module installed, like the other settings.

## [20.0.1.0.1] - 2026-09-28

Requires `pos_nm_multicurrencies` 20.0.2.1.0 (reading of the amounts typed
with a thousands separator).

### Fixed
- **Currencies without decimals (XPF, JPY...)**: the amount received typed
  in the exchange popup was read back wrong once formatted with its
  thousands separator (25,000 XPF became 25 XPF): the operation, its
  commission and its receipt were recorded for 25 XPF.
- **Rate of the popup and the receipt**: given in the direction where it is
  at least 1, with 2 to 4 decimals whatever the currencies: 0.0084 USD for
  1 XPF read "1 XPF = $ 0.01", it now reads "1 USD = 119.05 XPF".

## [20.0.1.0.0] - 2026-09-26

First version, on `pos_nm_multicurrencies` 20.0.2.0.0.

### Added
- **Exchange operation** (`pos.nm.exchange`): from the *Currency Exchange*
  entry of the register menu, between any two cash currencies of the point
  of sale; the popup quotes the amount handed back, the rate and the
  commission as the cashier types (`get_quote`), lets the cashier pick the
  customer and add a note, records the operation (`create_from_ui`) and
  prints the exchange receipt (`pos_exchange_receipt`).
- **Amounts**: notes received valued at the cash rate of the currency
  (payment rate), notes handed back at its change rate, rounded down to the
  change rounding of the currency; the commission is the difference of the
  two values.
- **Commissions per currency** on `pos.nm.currency.setting`: percentage,
  fixed part and minimum, logged in the chatter like the rates.
- **Point of sale settings**: counter enabled, commission income account,
  customer identification threshold.
- **Accounting**: two statement lines of the cash journal of the session
  (one per currency, foreign lines carrying the currency and the notes),
  both with the commission account as counterpart; the drawers of both
  currencies move accordingly.
- **Closing popup**: block with the operations and the total of the
  commissions; **Sales Details** report: *Currency Exchange* table;
  **session form**: *Exchange Commissions* button.
- **Backend**: list, form and pivot of the operations (*Point of Sale ->
  Orders -> Currency Exchanges*), grouped by point of sale, session,
  cashier or currency.
- Tests: quotes (main to foreign, foreign to main, fixed rates, RPC
  checks), operation with its lines, drawers, closing data, report and
  position, foreign to main, checks (drawer, customer threshold, account,
  disabled counter, too small, closed session); one register tour.
