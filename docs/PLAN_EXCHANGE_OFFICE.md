# Work plan: the exchange office vertical (20.0.3.0.0)

Goal: make `pos_nm_currency_exchange` the only tool a money changer needs,
from one counter to an office with several counters. The module already has
the operation (quote, commission, rounding, drawers), the identity document
and the exchange register (list, Excel, PDF). This plan adds what is missing,
in five lots that can ship one by one. Every lot keeps the rules of
`docs/DESIGN.md`: operations are recorded by `create_from_ui` only, never
edited or deleted, the server recomputes every check.

## Lot 1 - Exchange office and its counters

- New model `pos.nm.exchange.office` (*Exchange Office*): name, company,
  address (`partner_id`), license number, compliance officer (`user_id`),
  counters (`pos.config.nm_exchange_office_id`), active.
- The office carries the **rules** shared by its counters: license, the
  identification thresholds (customer, document, origin of funds, review),
  customer always required, linked operations period. A counter outside any
  office keeps its own fields (no change for current users).
  `pos.config._nm_rules()` returns the effective rules: every check
  (`_nm_identification`, `get_customer_document`, receipt license, rate
  board) reads it instead of the fields of the point of sale.
- The counters of an office share the currency of the office (constraint):
  the thresholds are in that currency.
- **Same rates at every counter**: *Apply to the counters* copies the
  exchange settings of a reference counter (Exchange Sell Margin, commission
  percent / fixed / minimum, and the cash rate fields of the parent: rate
  mode, Cash Rate Margin, fixed rates) to the other counters of the office;
  *Rate differences* lists the settings that differ. Logged in the chatter of
  each setting (parent `_NM_LOGGED_FIELDS`).
- Linked operations: summed at every counter of the company (unchanged).

## Lot 2 - Regulatory register and identification thresholds

- New thresholds (office, else point of sale), 0 = never:
  - *Origin of funds required above*: origin of funds (selection: salary,
    savings, business, sale of an asset, inheritance / gift, other) and its
    note, asked in the popup, frozen on the operation.
  - *Review above*: the operation is flagged *To review* for the compliance
    officer (activity on the operation), never blocked at the counter.
- Customer declarations frozen on the operation: politically exposed person
  (declared by the customer), purpose of the operation (travel, business,
  other), address of the customer (copied from the contact).
- Compliance fields editable by POS Administrators only, logged in the chatter:
  `compliance_state` (none / to review / reviewed / reported), compliance
  note. `write` keeps refusing every other field.
- **Inalterability**: every operation gets a hash at creation (SHA-256 of
  its frozen fields and of the hash of the previous operation of the
  company: a chain, under an advisory lock), and the cancellation its own
  hash. *Check Register Integrity* (company / office) recomputes the chain
  and reports the first operation that does not match, like the
  inalterability check of accounting.
- **Register closings** (`pos.nm.exchange.register.closing`): the register
  of a period, office or company, is closed by a POS Administrator: counts, totals per
  currency, last reference and last hash are frozen, the PDF register is
  generated and attached. A period cannot be closed twice; the closings are
  gapless too.
- The PDF register gains the office, its address and license, the new
  customer fields, the compliance flags and the hash of the last operation.

## Lot 3 - Rate board on the customer screen

- Public page `/pos_nm_exchange/board/<config_id>?access_token=...` (the
  access token of the point of sale, the one of the customer display; an
  office has its own token and page `/pos_nm_exchange/office_board/<id>`):
  full screen, large type, rows of `pos.config._nm_rate_board()` (we buy /
  we sell per unit and for the typical amount, commission rule), license,
  date and time. Refreshed by a JSON route every N seconds (setting, default
  60 s), without reloading; the last rates stay on screen while the network
  is lost, with a discreet marker.
- Works on any screen: the customer display of Odoo, a TV in the window, a
  tablet. The point of sale form gives the URL and a button to open it.
- Option *Rate board on the customer display*: the idle screen of the Odoo
  customer display shows the board instead of the logo (template extension
  of `point_of_sale.CustomerDisplay`, iframe of the page above).

## Lot 4 - Note stock by denomination

- Denominations: the coins and bills of POS Multi-Currency Cash (`pos.bill`
  with its `currency_id`, empty for the currency of the point of sale),
  already counted at opening and closing (`opening_details` /
  `closing_details` of `pos.session.currency.detail`, `{value: quantity}`).
  *Load the standard denominations* fills the usual ones of EUR, USD, GBP,
  CHF, JPY, CAD, AUD, XPF, ... for a currency.
- `pos.nm.note.move`: session, currency, denomination value, quantity
  (signed), origin (exchange, cancellation, transfer), operation / transfer.
  Never edited. Stock of a drawer during a session = opening count by
  denomination + moves of the session.
- Option per point of sale *Track the notes by denomination*: the popup
  asks the notes received by denomination (must add up to the amount
  received) and proposes the notes handed back from the stock (largest
  first, within the stock), editable, which must add up to the amount handed
  back. A stock shortfall is a warning: cash sales in a foreign currency
  move the drawer without denominations, the next count corrects it.
- Closing popup: the expected quantity of each coin/bill next to the count.
- Report *Note Stock*: per drawer, currency and denomination.

## Lot 5 - Transfers between counters

- `pos.nm.exchange.transfer`: office, from counter, to counter, currency,
  lines per denomination (or an amount), state draft / sent / received /
  cancelled. *Send*: cash out on the open session of the sending counter
  (statement line, counterpart the transit account of the office), stock
  moves out. *Receive*: cash in on the open session of the receiving counter,
  stock moves in. The notes in transit are the balance of the transit
  account.
- Also from the register: *Send notes* / *Receive notes* in the menu.
- Consolidated view of the office: drawers of every counter per currency
  (expected cash of the open sessions), notes in transit, operations of the
  day, commissions.

## Status

- Lot 1: done (office, rules, rate sync, views, tests `tests/test_office.py`).
- Lot 2: done server side, back office and register popup (declarations);
  a tour of the declarations is still to write.
- Lot 3: done (pages, JSON refresh, customer display idle screen, tests of
  the routes).
- Lot 4: done (option, note moves, proposal from the stock, checks of the
  grids, cancellation, closing data, Note Stock report, receipt; tests
  `tests/test_note_stock.py`). Foreign currencies only: the currency of the
  point of sale has no count by denomination in POS Multi-Currency Cash.
- Lot 5: done (transfers, transit account, note moves, register RPCs,
  register menu entries *Send Notes* / *Receive Notes* and their popups,
  transfer slip, office drawers; tests `tests/test_transfer.py` and the
  tours `PosCurrencyExchangeTransferTour` /
  `PosCurrencyExchangeReceiveTour`).

## Order of work and checks

1. Lot 1 and Lot 2 (server side and back office, tests in
   `tests/test_office.py` and `tests/test_compliance.py`).
2. Lot 3 (controller, page, idle screen; tests of the routes and token).
3. Lot 2 at the register (popup fields), Lot 4, then Lot 5.
4. Migration 20.0.3.0.0 (hash chain of the existing operations, in order),
   translations, guide, screenshots, CHANGELOG.

The thresholds are configured by the operator: the module does not hard-code
the legal values of a country, the guide gives the French ones as an example.
