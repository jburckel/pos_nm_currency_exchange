# Design notes

Target of the first version (see the parent module for the primitives it relies on:
drawers per currency, cash rates and fixed rates, coins and notes, Currency Position,
deposits, counts per cashier).

## Operation

- One record per operation (`pos.nm.exchange`): session, cashier, customer (optional
  below the identification threshold), currency given by the customer and amount,
  currency handed back and amount, rate applied, commission, date.
- Two statement lines on the cash journal of the session, like a cash in and a cash
  out of `pos_nm_multicurrencies`: the notes received (positive, in their currency)
  and the notes handed back (negative, in their currency), each at the cash rate of
  its currency; the commission is the difference, posted on a commission income
  account set on the point of sale.
- The register: a "Currency Exchange" entry in the burger menu opening a popup
  (currency in, amount in, currency out with the computed amount, commission,
  customer), printing an exchange receipt through the ticket printer.

## Settings

- Per currency, on `pos.nm.currency.setting`: commission in percent, fixed
  commission, minimum commission.
- On the point of sale: commission income account, identification threshold
  (customer required above it), exchange receipt header text.

## Reporting

- Closing popup: exchange operations listed in the moves of each currency.
- Currency Position: unchanged (the operations are statement lines of the drawers).
- Session report: one block "Currency Exchange" with the number of operations and the
  commissions.
