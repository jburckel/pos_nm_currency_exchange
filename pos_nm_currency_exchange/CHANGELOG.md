# Changelog

All notable changes to the POS Currency Exchange module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
  **session form**: *Exchanges* button.
- **Backend**: list, form and pivot of the operations (*Point of Sale ->
  Orders -> Currency Exchanges*), grouped by point of sale, session,
  cashier or currency.
- Tests: quotes (main to foreign, foreign to main, fixed rates, RPC
  checks), operation with its lines, drawers, closing data, report and
  position, foreign to main, checks (drawer, customer threshold, account,
  disabled counter, too small, closed session); one register tour.
