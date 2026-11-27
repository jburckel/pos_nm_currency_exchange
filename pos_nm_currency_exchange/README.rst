=====================
POS Currency Exchange
=====================

Currency exchange counter inside the Odoo 20 Point of Sale: the customer
brings notes in one currency and leaves with another, minus a commission.
Built on `POS Multi-Currency Cash <https://apps.odoo.com/apps/modules/20.0/pos_nm_multicurrencies>`_
(required, included in the price shown on the Odoo Apps Store: 178 EUR in
total, 59 EUR for this module plus 119 EUR for POS Multi-Currency Cash;
already bought it? Contact us at odoo@natimai.solutions before buying this
module), which controls the cash drawer of every currency, its cash rates and its coins and notes.

Features
========

* **Exchange operation from the register menu**, between any two cash
  currencies of the point of sale: type the amount received, or the amount
  the customer wants handed back
* **Buy and sell rates**: notes received at the cash rate, notes handed
  back at a sell rate with its own margin, in favour of the shop; **rate
  margin** of every operation against the rates of Odoo
* **Commission per currency**: percentage, fixed part and minimum; the notes
  handed back are rounded down to the coins and notes of their currency
  (the cash rounding of the point of sale for its own currency), the
  remainder stays in the commission
* **Drawer checked** before handing back, in every currency
* **Exchange receipt** with the header and footer of the point of sale and
  the exchange license number; reprint from the register, PDF and email
  from the back office
* **Rate board** of the counter at the register, on the receipt printer or
  in PDF
* **Customer identification**: thresholds, linked operations over a period,
  identity document recorded on the operation
* **Cancellation** by a POS Administrator while the session is open and
  the drawer still holds the notes received; operations cannot be deleted
  nor edited (only their note, by a POS Administrator), gapless references
* **Two lines on the cash journal** of the session, one per currency, with
  the commission on a dedicated income account
* **Closing control** (cash moves of each currency and a Currency Exchange
  block), **Currency Position and Sales Details** show the operations
* **Exchange offices**: several counters sharing a license,
  identification rules and the same rates, applied from a reference
  counter
* **Compliance**: origin of funds and review thresholds, politically
  exposed person, review by the compliance officer; **inalterable
  register** (hash chain, integrity check) and **closings** of the register
  per period
* **Rate board on a screen** facing the customers (TV, tablet or the
  customer display of Odoo), refreshed by itself
* **Notes tracked by denomination**: notes received and handed back counted
  per coin and note, note moves, Note Stock report and expected quantities
  in the closing popup
* **Note transfers** between the counters of an office, through a notes in
  transit account, with gapless references and a transfer slip; drawers of
  every counter on the office
* **Operations listed** per point of sale, session and cashier, with a pivot
  of the commissions and rate margins, and an **exchange register** exported
  to Excel or printed in PDF for a period

Configuration
=============

1. Install POS Multi-Currency Cash and list the foreign currencies on the
   cash payment method of the point of sale.
2. *Point of Sale → Configuration → Settings*, section *Currency Exchange*:
   enable the counter, set the commission account and, if needed, the
   license number and the identification rules.
3. *Point of Sale → Configuration → Cash Currencies*: set the sell margin
   and the commission (percentage, fixed part, minimum) of every currency.
4. Optional, with several counters: *Point of Sale → Configuration →
   Exchange Offices*, create the office with its license, rules and
   *Notes in Transit Account*, add its counters and press *Apply Rates to
   the Counters*.

See the guide in ``doc/`` (PDF in ``static/description/``).

Dependencies
============

* ``point_of_sale``
* ``pos_nm_multicurrencies`` 20.0.2.1.0 or later (POS Multi-Currency Cash,
  included in the price shown on the Odoo Apps Store: 178 EUR in total,
  59 EUR for this module plus 119 EUR for POS Multi-Currency Cash; already
  bought it? Contact us at odoo@natimai.solutions before buying this module)

Models
======

* ``pos.nm.exchange``: the operations
* ``pos.nm.exchange.register.wizard``: period of the printed exchange
  register, integrity check and closing of a period
* ``pos.nm.exchange.office``: exchange offices, their counters, rules,
  rate board and drawers
* ``pos.nm.exchange.register.closing``: closings of the exchange register
* ``pos.nm.note.move`` and ``pos.nm.note.stock``: coins and notes moved by
  denomination, and the note stock per session
* ``pos.nm.exchange.transfer``: note transfers between the counters of an
  office
* ``pos.nm.currency.setting`` (extended): sell margin and commissions per
  currency
* ``pos.config`` (extended): counter enabled, commission account, license
  number, identification rules, exchange office, notes by denomination,
  rate board
* ``pos.session`` (extended): operations of the session, closing data
* ``res.partner`` (extended): identity document of the customer
* ``account.bank.statement.line`` (extended): the lines of an operation
  cannot be deleted

Support
=======

* Email: odoo@natimai.solutions
* Website: https://www.natimai.solutions

License
=======

OPL-1 (Odoo Proprietary License), see ``LICENSE``.
