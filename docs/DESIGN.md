# Design notes

Version 20.0.1.0.0 (see the parent module for the primitives it relies on: drawers
per currency, cash rates and fixed rates, coins and notes, Currency Position,
deposits, counts per cashier).

## Operation

- One record per operation (`pos.nm.exchange`): session, cashier, customer (optional
  below the identification threshold), currency given by the customer and amount,
  currency handed back and amount, rate applied, commission, date.
- Two statement lines on the cash journal of the session, like a cash in and a cash
  out of `pos_nm_multicurrencies`: the notes received (positive, in their currency,
  at the cash rate of that currency) and the notes handed back (negative, in their
  currency, at the change rate of that currency). Both lines take the commission
  income account of the point of sale as counterpart, so the commission is the net
  of that account. The notes handed back are rounded down to the change rounding of
  their currency: the remainder stays in the commission.
- The quote (`_nm_quote`) is computed server side and called by the popup (debounced
  RPC `get_quote`); the operation (`create_from_ui`) checks the session, the account,
  the currencies, the customer threshold and the drawer balance of the currency
  handed back before posting.
- The register: a "Currency Exchange" entry in the burger menu opening a popup
  (currency in, amount in, currency out with the computed amount, rate, commission,
  customer, note), printing an exchange receipt through the ticket printer. The
  receipt template is a QWeb view added to the templates the POS loads
  (`ir.ui.view._get_xml_ids_to_load`).

## Settings

- Per currency, on `pos.nm.currency.setting`: commission in percent, fixed
  commission, minimum commission.
- On the point of sale: enable the counter, commission income account,
  identification threshold (customer required above it).

## Reporting

- Closing popup: the operations appear in the cash moves of each currency (parent
  module) and a "Currency Exchange" block gives the count and the commissions.
- Currency Position: unchanged (the operations are statement lines of the drawers).
- Session form: stat button with the commissions of the session.
- Session report: one block "Currency Exchange" listing the operations, with the
  number of operations and the total of the commissions.
- Back-office: list, form, pivot and search of `pos.nm.exchange` under Point of Sale.
