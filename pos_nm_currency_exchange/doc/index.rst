=====================
POS Currency Exchange
=====================

A currency exchange counter inside the Odoo 20 Point of Sale: the customer
brings notes in one currency and leaves with notes in another, minus a
commission. Built on POS Multi-Currency Cash, which controls the drawer of
every currency, its cash rates and its coins and notes.

Overview
========

Shops in tourist areas, hotels, campsites or border towns are regularly
asked to change money. With POS Multi-Currency Cash the register already
accepts foreign notes and hands change back in a foreign currency; this
module adds the operation without a sale:

* the cashier opens the **Currency Exchange** entry of the register menu,
  picks the currency received and the currency handed back, and types the
  amount received;
* the register quotes the amount to hand back at the cash rates of the
  point of sale, with the commission of the currency and the rounding to
  its coins and notes;
* the operation is recorded with the cashier and, when required, the
  customer, and an exchange receipt is printed;
* both drawers move: the notes received enter the drawer of their currency
  and the notes handed back leave the other one, on the cash journal of the
  session, with the commission posted on a dedicated income account;
* the operations appear in the closing control, in the *Currency Position*
  report and in the *Sales Details* report, and are listed per point of
  sale, session and cashier with a pivot of the commissions.

Requirements
============

* The **Point of Sale** application (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) 20.0, with at
  least one foreign currency on the cash payment method of the point of
  sale (see its guide: *Accept a currency in cash*).
* An **income account for the commissions**.

Configuration
=============

Enable the counter
------------------

Go to *Point of Sale -> Configuration -> Settings*, select your point of
sale and look at the **Currency Exchange** section:

* **Currency Exchange** (enabled by default): shows the entry in the menu
  of the register.
* **Commission account**: income account receiving the commissions. It is
  required to record an operation.
* **Customer required above**: value of an operation, in the currency of
  the point of sale, above which the customer must be identified. 0: never.

Commissions per currency
------------------------

Go to *Point of Sale -> Configuration -> Cash Currencies* and open the line
of the currency. The *Currency Exchange* group holds three values, all in
the currency of the point of sale except the percentage:

* **Exchange Commission (%)**: percentage of the value of the notes
  received;
* **Fixed Exchange Commission**: fixed part added to the percentage;
* **Minimum Exchange Commission**: the commission is at least this amount.

The commission of an operation is the one of the foreign currency involved
(the currency handed back when both are foreign). Every change of the
commissions is logged in the chatter of the line, like the rates.

Rates and coins and notes
-------------------------

The counter uses the cash rates of POS Multi-Currency Cash: the notes
received are valued at the rate applied to what a customer pays (rate of
Odoo with the margin, or the fixed rate), the notes handed back at the rate
applied to the change (the fixed change rate when set). The notes handed
back are rounded *down* to the **Change Rounding** of their currency, so
that the cashier never has to hand back coins that do not exist in the
drawer; the remainder stays in the commission.

Daily Workflow
==============

Exchanging currencies
---------------------

From any screen of the register, open the menu (top right) and press
**Currency Exchange**:

1. pick the currency **received from the customer** and type the amount;
2. pick the currency **handed back**; the amount, the rate applied
   (commission included) and the commission are quoted as you type. The
   arrow button swaps the two currencies;
3. when the value of the notes received exceeds the threshold of the point
   of sale, press **Customer** and pick the customer (create it if
   needed); the button turns red until it is done;
4. add a note if useful, then **Confirm**. The cash drawer opens, the
   exchange receipt is printed (received, handed back, rate, commission)
   and a notification sums the operation up.

The register refuses an operation when the drawer of the currency handed
back does not hold enough notes, when the amount is too small for a single
note, or when the same currency is picked on both sides.

Closing the session
-------------------

The closing popup shows a **Currency Exchange** block with the number of
operations, every operation (received, handed back, cashier) and the total
of the commissions. The notes received and handed back are already in the
expected amounts of their currencies: an exchange is a cash in on one
drawer and a cash out on the other, both listed in the moves of the
currency.

Reviewing the operations
------------------------

*Point of Sale -> Orders -> Currency Exchanges* lists every operation with
its reference, date, point of sale, session, cashier, customer, the notes
received and handed back, the rate and the commission; group by point of
sale, session, cashier or currency, and switch to the pivot for the
commissions per day and currency. The session form has an **Exchanges**
button with the total of the commissions.

The *Sales Details* report of a session ends with a *Currency Exchange*
table (operations and commissions), and the *Currency Position* report of
POS Multi-Currency Cash reflects the notes moved.

Accounting Notes
================

* An operation is two statement lines of the cash journal of the session:
  the notes received (positive, in their currency, valued at the cash rate)
  and the notes handed back (negative, in their currency, valued at the
  change rate). A line in the currency of the point of sale carries no
  foreign currency.
* Both lines use the **commission account** as counterpart: the difference
  between the two values, the commission, is what remains on that account.
  No separate entry is posted for the commission.
* The margin between the cash rates and the rates of Odoo is realized like
  for any sale in a foreign currency: when the notes are deposited or the
  drawer is revalued (see the guide of POS Multi-Currency Cash).
* The operations can be opened from their form (*Statement Lines* button)
  and cannot be edited; a mistaken operation is corrected with an opposite
  operation or a cash move.

Known Limitations
=================

* The counter works online: the quote and the recording are server calls.
* One operation involves two currencies; a customer changing several
  currencies at once makes several operations.
* The receipt is printed through the receipt printer of the register or
  the browser; there is no email of the exchange receipt.

Troubleshooting
===============

The Currency Exchange entry is missing from the menu
----------------------------------------------------

Check that **Currency Exchange** is enabled on the point of sale, then
close and reopen the register: the setting is read when it loads its data.

The operation is refused for the commission account
---------------------------------------------------

Set the **Commission account** in the *Currency Exchange* section of the
settings of the point of sale.

The amount handed back is lower than expected
---------------------------------------------

The notes handed back are rounded down to the **Change Rounding** of their
currency, and the commission includes the remainder. Lower the rounding on
the currency, or check its commission.

Disclaimer
==========

This module is provided by Natimai Solutions under the Odoo Proprietary
License v1.0. Exchange operations may be regulated in your country
(licensing, identification of the customer, registers): the module records
the operations and their customer, but the compliance with local
regulations remains the responsibility of the business.

Support
=======

* Email: odoo@natimai.solutions
* Website: https://www.natimai.solutions

License
=======

OPL-1 (Odoo Proprietary License), see the ``LICENSE`` file of the module.
