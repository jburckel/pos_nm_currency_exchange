=====================
POS Currency Exchange
=====================

Currency exchange counter inside the Odoo 20 Point of Sale: the customer
brings notes in one currency and leaves with another, minus a commission.
Built on `POS Multi-Currency Cash <https://github.com/jburckel/pos_nm_multicurrencies>`_,
which controls the cash drawer of every currency, its cash rates and its
coins and notes.

Features
========

* **Exchange operation from the register menu**, between any two cash
  currencies of the point of sale, quoted at its cash rates as you type
* **Commission per currency**: percentage, fixed part and minimum; the notes
  handed back are rounded to the coins and notes of their currency, the
  remainder stays in the commission
* **Exchange receipt** printed for the customer
* **Two lines on the cash journal** of the session, one per currency, with
  the commission on a dedicated income account
* **Closing control, Currency Position and Sales Details** show the
  operations
* **Customer identification** above a threshold
* **Operations listed** per point of sale, session and cashier, with a pivot
  of the commissions

Configuration
=============

1. Install POS Multi-Currency Cash and list the foreign currencies on the
   cash payment method of the point of sale.
2. *Point of Sale -> Configuration -> Settings*, section *Currency Exchange*:
   enable the counter, set the commission account and, if needed, the
   identification threshold.
3. *Point of Sale -> Configuration -> Cash Currencies*: set the commission
   (percentage, fixed part, minimum) of every currency.

Dependencies
============

* ``point_of_sale``
* ``pos_nm_multicurrencies`` (20.0)

Models
======

* ``pos.nm.exchange``: the operations
* ``pos.nm.currency.setting`` (extended): commissions per currency
* ``pos.config`` (extended): counter enabled, commission account, threshold
* ``pos.session`` (extended): operations of the session, closing data

Support
=======

* Email: odoo@natimai.solutions
* Website: https://www.natimai.solutions

License
=======

OPL-1 (Odoo Proprietary License), see ``LICENSE``.
