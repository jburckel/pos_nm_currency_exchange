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
  amount received, or the amount the customer wants handed back;
* the register quotes the operation: notes received at the cash rate of
  the point of sale (the buy rate), notes handed back at the sell rate of
  the counter, the commission of the currency, the rounding to the coins
  and notes, and what the drawer holds;
* the operation is recorded with the cashier and, when required, the
  customer and the identity document, and an exchange receipt is printed;
* both drawers move: the notes received enter the drawer of their currency
  and the notes handed back leave the other one, on the cash journal of the
  session, with the commission posted on a dedicated income account;
* a manager can cancel a mistaken operation while the session is open;
* the operations appear in the closing control, in the *Currency Position*
  report and in the *Sales Details* report, in a list with a pivot of the
  commissions and rate margins, and in an exchange register that can be
  exported or printed for a period;
* the rate board of the counter can be shown and printed at the register,
  or printed in PDF.

Requirements
============

* The **Point of Sale** application (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) **20.0.2.1.0 or
  later**, sold separately, with at least one foreign currency on the cash
  payment method of the point of sale (see its guide: *Accept a currency in
  cash*). An older version of POS Multi-Currency Cash does not work with
  this module: update it first.
* An **income account for the commissions** (type *Income* or *Other
  Income*).

Configuration
=============

Enable the counter
------------------

Go to *Point of Sale -> Configuration -> Settings*, select your point of
sale and look at the **Currency Exchange** section:

* **Currency Exchange** (enabled by default): shows the entries of the
  counter in the menu of the register.
* **Commission account**: income account receiving the commissions. Only
  income accounts can be chosen. It is required to record an operation.
* **Exchange licence number**: licence or registration number of your
  exchange activity, printed on the receipts and the rate board when set.
* **Customer required above**: value of an operation, in the currency of
  the point of sale, above which the customer must be identified.
* **Customer required for every operation**: every operation names its
  customer.
* **Identity document required above**: value above which the identity
  document of the customer is recorded on the operation.
* **Linked operations period (days)**: when above 0, the value compared to
  the two thresholds is the operation plus the operations of the same
  customer over that many days (see *Customer Identification*).
* **Print Exchange Rates**: prints the rate board of the point of sale in
  PDF.

Thresholds at 0 are never applied.

Commissions and sell margin per currency
----------------------------------------

Go to *Point of Sale -> Configuration -> Cash Currencies* and open the line
of the currency. The *Currency Exchange* group holds four values, the
amounts being in the currency of the point of sale:

* **Exchange Sell Margin (%)**: margin of the counter on the notes of this
  currency it hands back (see *Rates* below). Hidden with a fixed cash
  rate, where it is not used;
* **Exchange Commission (%)**: percentage of the value of the notes
  received;
* **Fixed Exchange Commission**: fixed part added to the percentage;
* **Minimum Exchange Commission**: the commission is at least this amount.

The commission of an operation is the one of the foreign currency involved
(the currency handed back when both are foreign). Every change of these
values is logged in the chatter of the line, like the rates.

Rates
-----

The counter buys at one rate and sells at another, always in favour of the
shop. The rates are given as units of the foreign currency for one unit of
the currency of the point of sale, like in POS Multi-Currency Cash:

* **Notes received** (buy rate): the cash rate of POS Multi-Currency Cash,
  that is the rate of Odoo with the **Cash Rate Margin** of the currency,
  or its **Fixed Rate**.
* **Notes handed back** (sell rate): the rate of Odoo divided by 1 + the
  **Exchange Sell Margin**. With a fixed cash rate, the lower of the
  **Fixed Rate** and the **Fixed Change Rate** (a Fixed Change Rate of 0
  means the Fixed Rate): the lower rate hands back fewer notes.

Example, point of sale in USD, rate of Odoo 2 EUR for 1 USD, Cash Rate
Margin and Exchange Sell Margin of 10 %: the counter buys euros at
2.20 EUR for 1 USD (100 EUR received are worth $ 45.45) and sells them at
1.82 EUR for 1 USD (100 EUR handed back are worth $ 55.00), before the
commission.

The difference with the rates of Odoo is the **Rate Margin** of the
operation (see *Accounting Notes*). On upgrade from a version before
20.0.2.0.0, the Exchange Sell Margin of each currency is set to its Cash
Rate Margin: check it.

Coins and notes
---------------

The notes handed back are rounded once, *down*, to the smallest coin or
note of their currency, so that the cashier never has to hand back coins
that do not exist in the drawer; the remainder stays in the commission,
which is never below the configured one:

* a foreign currency: its **Change Rounding**, else the rounding of the
  currency;
* the currency of the point of sale: the rounding method of **Total
  Rounding** in the settings of the point of sale, when enabled, else the
  rounding of the currency.

Receipt
-------

The exchange receipt prints the logo, the **Header** and **Footer** of the
point of sale (*Settings*, section *Bills & Receipts*, *Custom Header &
Footer*), the
exchange licence number and the company details. Write there the legal
notices your activity must show to the customer.

Who can do what
---------------

* **POS users** (cashiers) record operations at the register, reprint
  their receipts and show the rate board. They can read the operations but
  cannot change them.
* **POS Administrators** (*Point of Sale* access *Administrator*) also see
  the menus *Point of Sale -> Orders -> Currency Exchanges* and *Point of
  Sale -> Reporting -> Exchange Register*, the identity documents of the
  customers, can edit the note of an operation and cancel an operation.
* Nobody can delete an operation or one of its statement lines.
* With several companies, each user sees the operations of the companies
  he is allowed in.
* With the Employees module (``pos_hr``), the cashier of an operation is
  the employee logged in at the register, and he must be allowed on the
  point of sale; otherwise it is the user.

Daily Workflow
==============

Exchanging currencies
---------------------

From any screen of the register, open the menu (top right) and press
**Currency Exchange**:

1. pick the currency **received from the customer** and type the amount;
2. pick the currency **handed back**. The amount handed back, the rate, the
   value of the notes received, the commission and the balance of the
   drawer (**In the drawer**) are quoted as you type. The arrow button
   swaps the two currencies;
3. when the customer asks for an exact amount, type it in **Handed back**
   instead: the amount to receive is computed, rounded up to the coins of
   the received currency, and the hint "Amount to receive computed from the
   amount handed back" is shown. When you leave the field it shows the
   amount actually handed back, which can be slightly higher when the notes
   cannot make the amount exactly. Typing in **Received** again goes back
   to the normal quote;
4. when the customer must be identified, the **Customer** button turns red
   with the reason: press it and pick the customer (create it if needed).
   When the identity document is required, its fields appear: type,
   issuing country and expiry date are prefilled from the contact, and the
   number field only shows the last 4 characters of the recorded number
   as a hint. Type, number and expiry date are mandatory. **Nationality**
   and **Date of birth** are shown empty: left empty, they keep the values
   of the contact. For the same document (same type, number left empty)
   the number and the other fields left empty keep the values of the
   contact too; for another document, type its number;
5. add a note if useful, then **Confirm**. The cash drawer opens, the
   exchange receipt is printed and a notification sums the operation up.

**Confirm** stays disabled while a quote is computed, and when the drawer
of the currency handed back does not hold the amount (the *In the drawer*
line is then red, with the refusal).

When the connection drops while confirming, the popup says that the
operation may have been recorded: confirm again once the connection is
back. Until then the amounts, currencies, customer, document and note
cannot be changed. An operation already recorded is not recorded twice,
and its receipt is printed. When the connection drops while the quote is
computed, the popup says so and requests the quote again a few seconds
later.

When the counter cannot work at this point of sale, the **Currency
Exchange** entry shows the reason instead of the popup: no foreign currency
on the cash payment method, or no commission account.

The coin warning
----------------

An orange warning appears when the amount received in a foreign currency
cannot be made up with its coins and notes, for instance 1,106 XPF with
5 XPF coins. The step checked is the **Payment Rounding** of the currency,
else its **Change Rounding** when its **Remainder of the Change** is *Kept
as rounding*. The warning does not block the operation: check the notes
actually received and correct the amount if needed.

Refusals
--------

The register refuses an operation, with a message, when:

* the drawer of the currency handed back does not hold the amount, the
  currency of the point of sale included (the balance is the one of the
  closing control: opening, cash sales and change, cash moves and
  exchanges of the session);
* the amount is too small: once the commission is deducted, no note can be
  handed back;
* the same currency is picked on both sides;
* the customer, or a valid identity document, is required and missing, or
  the document has expired;
* the quote changed between the popup and the server (rate, margin or
  commission changed meanwhile): "The quote changed: ...". Type the amount
  again to get the new quote, then confirm;
* the session is not open, or the counter is disabled.

Reprinting a receipt
--------------------

The **Exchange Operations** entry of the register menu lists the operations
of the session (reference, date, operation, received, handed back,
customer). **Reprint** prints the receipt again, marked *COPY*; an
operation cancelled since is marked *CANCELLED* with the date and time.

Showing the rates
-----------------

The **Exchange Rates** entry of the register menu shows the rate board of
the counter, one line per foreign cash currency:

* **We buy**: value of 1 unit of the notes received (cash rate, before the
  commission), and **You receive**: what the customer receives for a
  typical amount, commission deducted and rounded to the notes;
* **We sell**: price of 1 unit of the notes handed back (sell rate, before
  the commission), and **You pay**: what the customer pays for a typical
  amount, commission included;
* **Commission**: percentage, fixed part and minimum.

The typical amount is the power of 10 nearest to 100 units of the currency
of the point of sale (100 EUR, 10,000 XPF, 1,000,000 VND). The amounts are
computed by the quote of the counter, so they match the operations.
**Print** prints the board on the receipt printer.

Cancelling an operation
-----------------------

A mistaken operation is cancelled, not corrected by another operation: an
opposite operation would charge the commission again and round the notes
again, and a cash move would leave the commission on the commission
account.

A POS Administrator opens the operation (*Point of Sale -> Orders ->
Currency Exchanges*) and presses **Cancel Operation**, then confirms. This
is possible while the session of the operation is open and when the drawer
still holds the notes received (the customer gets them back). Two statement
lines exactly opposite to the original ones are posted on the session:
same amounts in both currencies, same counterpart account. Both drawers and
the commission account return to their state before the operation.

The operation turns **Cancelled**, with the date and the user, a message is
posted on the session and on the operation, and it no longer counts in the
commissions, the closing summary and the reports. Its receipt, reprinted,
is marked *CANCELLED*.

Once the session is closed, an operation cannot be cancelled any more.
Correct it then with an opposite operation (the commission and the rounding
apply again; set the commission of the currency to 0 meanwhile if you
refund it) or with cash moves of each currency, and ask your accountant to
move the commission back from the commission account.

Closing the session
-------------------

The closing popup shows a **Currency Exchange** block whenever the session
has operations: the number of operations, every operation (received,
handed back, cashier), the total of the commissions, the **Rate Margin**
and the number of cancelled operations. The notes received and handed back
are already in the expected amounts of their currencies: an exchange is a
cash in on one drawer and a cash out on the other, both listed in the moves
of the currency.

Customer Identification
=======================

The thresholds help you apply the identification rules of your country;
the module records what the cashier enters, it does not check identity
documents against any register.

* The value compared to the thresholds is the value of the notes received,
  in the currency of the point of sale.
* With a **Linked operations period**, the operations done (not
  cancelled) by the same customer over the last days, at every point of
  sale of the company, are added, converted to the currency of the point
  of sale. When this total exceeds a threshold, the popup shows "With
  the linked operations of the customer" and the total; otherwise the
  other operations of the customer are not shown. Without a customer, only the operation counts:
  enable **Customer required for every operation** so that the rule always
  applies.
* Above **Customer required above**, the operation needs a customer.
* Above **Identity document required above**, it needs a customer and a
  valid identity document: type (Passport, Identity Card, Driving Licence,
  Residence Permit, Other), number, issuing country, expiry date,
  nationality and date of birth. An expired document is refused.

The server checks these rules again when the operation is recorded. The
document typed at the register, when it differs from the one recorded,
is saved on the contact (tab **Identity Document** of the contact form) and a copy is kept on the operation with
the name of the customer: changing or renaming the contact later does not
change the operations recorded. The receipt prints the name of the customer
and the type of document with the last 4 characters of its number only
(for instance "Passport \*\*\*\*4567").

The identity documents are visible to POS Administrators only; in the
popup, the cashier sees the type, issuing country, expiry date and last 4
characters of the number of the selected customer. A document changed at
the register is logged on the contact. The contact of an internal user, even
archived, is changed by a POS Administrator only (the document then stays
on the operation); a customer with a portal account is a customer like
any other.

Reviewing the operations
========================

Currency Exchanges
------------------

*Point of Sale -> Orders -> Currency Exchanges* (POS Administrators) lists
the operations with their reference, date, point of sale, cashier,
customer, the notes received and handed back, the commission, the rate
margin and the status. It opens with the filter **Done**; the filter
**Cancelled** shows the cancelled ones. Other filters: *Today*, *With
Customer*, *Purchase of foreign currency*, *Sale of foreign currency*,
*Cross exchange*; group by point of sale, session, cashier, operation type,
status, currency or date. The pivot gives the commissions, rate margins and
values received per day, status and currency.

The operation type is seen from the shop: *Purchase of foreign currency*
when it receives foreign notes, *Sale of foreign currency* when it hands
foreign notes back, *Cross exchange* between two foreign currencies.

The form of an operation shows its amounts, the **Rate Applied**
("1 USD = 119.33 XPF"), the commission, the rate margin, the identity
document and the chatter. Its buttons:

* **Send by E-mail** (when the operation has a customer): sends the
  receipt in PDF with the template *Currency Exchange: Send Receipt*;
* **Print**: the receipt in PDF (*Exchange Receipt*);
* **Cancel Operation** (see above);
* **Statement Lines**: the two lines of the operation, and the two lines
  of its cancellation.

Only the **Note** can be edited, by a POS Administrator; its changes are
logged in the chatter.

The session form has a button with the total of the commissions and
"Exchanges: N", the number of operations done; it opens them.

Sales Details
-------------

The *Sales Details* report ends with a *Currency Exchange* table: every
operation with its session, amounts, commission and rate margin, then the
totals, one line per currency of the points of sale, and the list of the
cancelled operations, which are not counted. Printed from a session, it
covers the operations of the session; run from *Point of Sale ->
Reporting -> Sales Details* for a period, it covers the operations dated
in that period on the selected points of sale (all of them when none is
selected), open sessions included. The *Currency Position* report of POS
Multi-Currency Cash reflects the notes moved.

Exchange Register
-----------------

*Point of Sale -> Reporting -> Exchange Register* (POS Administrators)
lists every operation in the order of its reference, the cancelled ones
included (greyed, with their status), with the cashier, the operation
type, the amounts, the rate, the commission, the rate margin, the customer
name and the identity document. The references follow each other without
gap. Export it to Excel with the standard *Export* action.

**Print Register** asks for a period (**From**, **To**, by default from the
start of the month to now) and the **Points of Sale** (all of them when
empty), and prints the register in PDF (A4 landscape) with the totals per
currency: number of operations, received, handed back, balance,
commissions and rate margins. The cancelled operations are listed but not
counted in the totals.

Rate board in PDF
-----------------

The rate board described above is also printed in PDF (*Exchange Rates*)
with **Print Exchange Rates** in the settings, or from the *Print* menu of
the point of sale records (list view of *Point of Sale -> Dashboard*).

Accounting Notes
================

* An operation is two statement lines of the cash journal of the session:
  the notes received (positive, in their currency, at their received value)
  and the notes handed back (negative, in their currency, at their handed
  value). A line in the currency of the point of sale carries no foreign
  currency. The lines carry the cashier as partner.
* Both lines use the **commission account** as counterpart: the difference
  between the two values, the commission, is what remains on that account.
  No separate entry is posted for the commission.
* The **Rate Margin** of an operation is what its rates earn against the
  rates of Odoo of the day: value of the notes received at the rate of Odoo
  less their received value, plus the handed value less the value of the
  notes handed back at the rate of Odoo. It is realized like for any sale
  in a foreign currency: by the drawer revaluation of POS Multi-Currency
  Cash, or when the notes are deposited (see its guide). The commission
  plus the rate margin is the income of the operation. With fixed rates
  above the rates of Odoo, the rate margin can be negative: it shows the
  loss.
* A cancellation posts two lines opposite to the original ones, on the
  same counterpart account: the commission is reversed.
* The operations and their statement lines cannot be deleted; the
  references (``EXC/YYYY/NNNNN``) have no gap.

Upgrading from 20.0.1.x
=======================

* Update POS Multi-Currency Cash to 20.0.2.1.0 or later first: the
  installation and the upgrade are refused otherwise.
* The **Exchange Sell Margin** of each currency is set to its Cash Rate
  Margin (a negative margin becomes the sell margin that keeps the same
  sell rate, 2.04 % for -2 %): the notes handed back are now priced at the
  sell rate, in favour of the shop. Check the margins and the rate board
  before opening the registers.
* The operations already recorded get their user, status, rate, rate
  margin and customer name. Their rate margin is computed at the rate of
  Odoo of their day: the operations made before show the loss of the old
  pricing of the notes handed back.
* The reference sequence becomes gapless. Operations can no longer be
  deleted: use **Cancel Operation**.
* The drawer of the currency of the point of sale is now checked: count
  its opening amount.
* Close the sessions, or reload every register, after the upgrade: a
  register still running the previous version cannot record operations.
* An operation one of whose statement lines was deleted with 20.0.1.x is
  reported in the server log and by a message on the operation: correct
  the drawer with a cash move.

Known Limitations
=================

* The counter works online: the quote and the recording are server calls.
* One operation involves two currencies; a customer changing several
  currencies at once makes several operations.
* An operation can only be cancelled while its session is open.
* The rate board is not shown on the customer display.

Troubleshooting
===============

The Currency Exchange entry is missing from the menu
----------------------------------------------------

Check that **Currency Exchange** is enabled on the point of sale, then
close and reopen the register: the setting is read when it loads its data.

A message shows instead of the popup
------------------------------------

Add a foreign currency to the cash payment method of the point of sale, or
set the **Commission account** in the *Currency Exchange* section of the
settings, then reload the register.

The commission account is refused
---------------------------------

Only an account of type *Income* or *Other Income* can receive the
commissions.

The amount handed back is lower than expected
---------------------------------------------

The notes handed back are priced at the sell rate and rounded down to the
**Change Rounding** of their currency (the Total Rounding of the point of
sale for its own currency), and the commission includes the remainder.
Check the Exchange Sell Margin, the rounding and the commission of the
currency.

The drawer does not hold the amount
-----------------------------------

The drawer of the currency handed back must hold the amount, as counted by
the closing control. Exchange in the other direction, or record a cash in
of that currency first. For the currency of the point of sale, check that
the opening amount was counted.

An orange warning about coins and notes
---------------------------------------

The amount received cannot be made up with the coins of the currency (see
*The coin warning*). It does not block the operation.

"The quote changed"
-------------------

A rate, a margin or a commission changed after the quote. Type the amount
again: the popup quotes the new amount, then confirm.

The connection was lost while confirming
----------------------------------------

Confirm again once the connection is back: an operation already recorded
is not recorded twice.

An operation cannot be cancelled
--------------------------------

Only a POS Administrator can cancel, while the session of the operation is
open, and when the drawer still holds the notes received. After the
closing, see *Cancelling an operation*.

The identity document is refused
--------------------------------

Type, number and expiry date are mandatory, and the document must not be
expired. The threshold may be reached with the linked operations of the
customer: the popup shows their total.

Delete is missing on the operations
-----------------------------------

The operations cannot be deleted, so that the register stays complete:
cancel the operation instead.

The cashier cannot find Currency Exchanges or Exchange Register
---------------------------------------------------------------

These menus are for POS Administrators. Cashiers use the **Exchange
Operations** entry of the register menu.

Disclaimer
==========

This module is provided by Natimai Solutions under the Odoo Proprietary
License v1.0. Exchange operations may be regulated in your country
(licensing, identification of the customer, registers, reporting): the
module helps you keep the operations, their customer and identity document
and the exchange register, but it does not make your activity compliant by
itself; the compliance with local regulations remains the responsibility of
the business.

Support
=======

* Email: odoo@natimai.solutions
* Website: https://www.natimai.solutions

License
=======

OPL-1 (Odoo Proprietary License), see the ``LICENSE`` file of the module.
