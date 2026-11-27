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
* a POS Administrator can cancel a mistaken operation while the session is
  open and the drawer still holds the notes received;
* the operations appear in the closing control, in the *Currency Position*
  report and in the *Sales Details* report, in a list with a pivot of the
  commissions and rate margins, and in an exchange register that can be
  exported or printed for a period;
* the rate board of the counter can be shown and printed at the register,
  or printed in PDF;
* several counters of one licensed place of business can form an
  **exchange office**: they share its license, its identification rules
  and the same rates, and the office shows the drawers of every counter;
* above thresholds you set, the customer declares the origin of the funds,
  and the operation is flagged *To Review* for the compliance officer;
* every operation is chained into an inalterable register (hash chain),
  which can be checked and closed per period;
* the rate board can be shown full screen on a screen facing the
  customers, or on the customer display of Odoo, and reloads the rates by
  itself;
* the foreign coins and notes received and handed back can be counted by
  denomination, with the stock of each drawer, and notes can be sent from
  one counter of an office to another.

All of this is optional: a single counter without exchange office works as
before.

Requirements
============

* The **Point of Sale** application (``point_of_sale``), Odoo 20.
* **POS Multi-Currency Cash** (``pos_nm_multicurrencies``) **20.0.2.1.0 or
  later**, included in the price shown on the Odoo Apps Store: 178 EUR in
  total, 59 EUR for this module plus 119 EUR for POS Multi-Currency Cash
  (already bought it? Contact us at odoo@natimai.solutions before buying
  this module), with at least one foreign currency on the
  cash payment method of the point of sale (see its guide: *Accept a
  currency in cash*). An older version of POS Multi-Currency Cash does not
  work with
  this module: update it first. With 20.0.2.1.1 or later, the opening of
  the Cash block of the main currency in the closing popup is shown
  correctly when the session has exchange operations (before, it was only
  a display error: the counted and posted amounts were right).
* An **income account for the commissions** (type *Income* or *Other
  Income*).
* To transfer notes between the counters of an exchange office: a
  **notes in transit account** (type *Current Assets*).

Configuration
=============

Enable the counter
------------------

Go to *Point of Sale → Configuration → Settings*, select your point of
sale and look at the **Currency Exchange** section:

* **Currency Exchange** (enabled by default): shows the entries of the
  counter in the menu of the register.
* **Commission account**: income account receiving the commissions. Only
  income accounts can be chosen. It is required to record an operation.
* **Exchange license number**: license or registration number of your
  exchange activity, printed on the receipts and the rate board when set.
* **Exchange office**: the exchange office of this counter (see *Exchange
  office and counters*). With an office, the license and the
  identification thresholds below are hidden: those of the office apply.
* **Customer required above**: value of an operation, in the currency of
  the point of sale, above which the customer must be identified.
* **Customer required for every operation**: every operation names its
  customer.
* **Identity document required above**: value above which the identity
  document of the customer is recorded on the operation.
* **Linked operations period (days)**: when above 0, the value compared to
  the thresholds is the operation plus the operations of the same
  customer over that many days (see *Customer Identification*).
* **Origin of funds required above**: value above which the customer
  declares the origin of the funds (see *Compliance thresholds*).
* **Review above**: value above which the operation is flagged *To Review*
  for the compliance officer. It is never refused.
* **Track the notes by denomination**: the foreign notes received and
  handed back are counted by coin and note (see *Notes by denomination*).
* **Rate board on the customer display**: the customer display of Odoo
  shows the rate board while no order is in progress.
* **Rate board address**: address of the full-screen rate board of this
  counter, for a screen facing the customers (see *Rate board on a
  screen*).
* **Print Exchange Rates**: prints the rate board of the point of sale in
  PDF.

Thresholds at 0 are never applied.

Commissions and sell margin per currency
----------------------------------------

Go to *Point of Sale → Configuration → Cash Currencies* and open the line
of the currency. The *Currency Exchange* group holds four values, the
amounts being in the currency of the point of sale:

* **Exchange Sell Margin (%)**: margin of the counter on the notes of this
  currency it hands back (see *Rates* below). A new currency starts from
  its Cash Rate Margin (a negative one becomes the sell margin keeping the
  same sell rate, as on upgrade). Hidden with a fixed cash rate, where it
  is not used;
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
2 × 1.10 = 2.20 EUR for 1 USD (100 EUR received are worth $ 45.45) and
sells them at 2 / 1.10 = 1.8182 EUR for 1 USD (100 EUR handed back are
worth $ 55.00), before the commission.

The difference with the rates of Odoo is the **Rate Margin** of the
operation (see *Accounting Notes*). On upgrade from 20.0.1.x, the
Exchange Sell Margin of each currency is set to its Cash
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
exchange license number and the company details. Write there the legal
notices your activity must show to the customer. With the notes counted by
denomination, the receipt lists the notes under the amounts.

Exchange office and counters
----------------------------

An exchange office is one licensed place of business with one or more
counters (points of sale). It is optional: a counter outside any office
keeps its own settings.

Go to *Point of Sale → Configuration → Exchange Offices* and press
**New**. Give the office a name, then fill in:

* group *Office*: the **Address** (printed on the exchange register and
  the rate board), the **Exchange License Number**, the **Compliance
  Officer** (he receives an activity for every operation flagged *To
  Review*) and the **Notes in Transit Account** (see *Notes in transit
  account*);
* group *Identification*: **Customer Required for Every Operation**,
  **Customer Required Above**, **Identity Document Required Above**,
  **Origin of Funds Required Above**, **Review Above** and **Linked
  Operations Period** (days). They work like the settings of the same name
  of a point of sale, in the currency of the company.

The license and the rules of the office replace those of its counters. To
add a counter, set its **Exchange office** in the *Currency Exchange*
section of the settings of the point of sale, or add it in the
**Counters** tab of the office. The counters of an office must use the
currency of its company.

The smart buttons of the office open its **Counters**, its
**Operations** and its note **Transfers**.

Same rates at every counter
---------------------------

In the **Counters** tab of the office, choose the **Reference Counter**:
the counter whose rates the others copy, and whose rates the rate board of
the office shows. Then, with two counters or more:

* **Apply Rates to the Counters** copies, for every currency of the
  reference counter, the cash rate (rate mode, margin, fixed rates), the
  roundings of the coins and notes, the **Exchange Sell Margin (%)** and
  the commissions to the other counters. The changes of the rates, the
  margins and the commissions are logged in the chatter of the currency
  (not those of the roundings). A counter that does not take the currency in
  cash is skipped and named in a warning;
* **Rate Differences** lists what still differs from the reference
  counter.

Apply the rates again after each change of the reference counter.

Compliance thresholds
---------------------

Two thresholds help you follow the anti-money laundering rules of your
country. They are set on the exchange office, or in the settings of a
point of sale outside any office, in the currency of the point of sale; at
0 they are never applied. The linked operations of the customer count,
like for the other thresholds.

* **Origin of funds required above**: the operation needs a customer, and
  the customer declares the origin of the funds. *Other* needs details.
* **Review above**: the operation is flagged *To Review*. It is never
  refused at the counter. An activity goes to the **Compliance Officer**
  of the office.

An operation whose customer declares being a politically exposed person is
flagged *To Review* too. Choose a POS Administrator as compliance officer:
only POS Administrators can review the operations.

Rate board on a screen
----------------------

Each counter has a public rate board page for a TV, a tablet or any
screen facing the customers. Its address is the **Rate board address** in
the *Currency Exchange* section of the settings of the point of sale. It
holds the access token of the point of sale, the one of its customer
display: share it only with the screens of the counter.

An exchange office has its own page, in the **Rate Board** tab of the
office (POS Administrators): the **Rate Board Address** shows the rates of
the reference counter under the name, address and license of the office.
**Board Refresh (seconds)** sets how often the page reloads the rates (60
by default, 10 at least), also for the pages of its counters. **New
Address** gives the office page a new address: the screens showing the old
one stop receiving the rates (they keep the last rates with "Connection
lost: last rates shown", and show nothing once the page is reloaded).

To show the board on the customer display of Odoo, tick **Rate board on
the customer display** in the settings of the point of sale.

Notes by denomination
---------------------

POS Multi-Currency Cash already counts the coins and notes of each
foreign currency at opening and closing. This module can follow them
during the session too:

1. Go to *Point of Sale → Configuration → Coins/Bills* and check that the
   coins and notes of each foreign currency exist, with their
   **Currency** set (see the guide of POS Multi-Currency Cash).
2. In the settings of the point of sale, tick **Track the notes by
   denomination**.

The option applies to the foreign cash currencies that have coins and notes
at this point of sale. The currency of the point of sale is not tracked:
it has no count by denomination. Count the opening by coins and notes, so
that the stock of the drawer starts right.

Notes in transit account
------------------------

Notes sent from one counter of an office to another pass through the
**Notes in Transit Account** of the office: a current assets account
(type *Current Assets*). Create one in your chart of accounts if needed,
for instance "Notes in transit", and set it on the office. Its balance is
the value of the notes sent and not received yet. Without it, notes
cannot be transferred.

Who can do what
---------------

* **POS users** (cashiers) record operations at the register, reprint
  their receipts and show the rate board. They can read the operations but
  cannot change them.
* **POS Administrators** (*Point of Sale* access *Administrator*) also see
  the menus *Point of Sale → Orders → Currency Exchanges* and *Point of
  Sale → Reporting → Exchange Register*, the identity documents of the
  customers, can edit the note of an operation and cancel an operation.
* At an office with another enabled counter, POS users also send and
  receive notes at the register (*Send Notes*, *Receive Notes*), and they
  see the *Note Stock* of their drawer when the notes are tracked.
* POS Administrators also manage the exchange offices (*Point of Sale →
  Configuration → Exchange Offices*, with the **Drawers** and **Rate
  Board** tabs), the note transfers (*Point of Sale → Orders → Note
  Transfers*), and see *Point of Sale → Reporting → Note Stock*, *Note
  Moves* and *Exchange Register Closings*.
* Only POS Administrators see the declarations of the customer and review
  the operations (**Compliance**, **Compliance Note**), check the
  integrity of the register and close it.
* Nobody can delete an operation or one of its statement lines, a note
  move, a register closing or a note transfer once sent.
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
   as a hint. Type, number and expiry date are mandatory; for a document
   without expiry date (an older identity card), tick **No expiry date**
   instead. **Nationality** and **Date of birth** are shown empty: left empty, they keep the values
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

Declarations of the customer
----------------------------

Above the **Origin of funds required above** or the **Review above**
threshold, once the customer is picked, the popup shows **Declarations of
the customer**:

* **Origin of the funds**: Salary or pension, Savings, Business income,
  Sale of an asset, Inheritance or gift, Other. Required above the origin
  of funds threshold; for *Other*, type the **Details of the origin of the
  funds**;
* **Purpose of the operation**: Travel, Business, Studies, Family support,
  Other;
* **Politically exposed person (or a relative or close associate of
  one)**: tick it when the customer declares it. The operation is then
  flagged *To Review*.

Above the review threshold only, the declarations are asked but not
required. They are frozen on the operation with the address of the
customer. The cashier is never blocked by a review: the compliance officer
checks the operation later (see *To Review*).

Counting the notes
------------------

With **Track the notes by denomination**, the popup widens and shows a
grid for each tracked foreign currency of the operation:

* **Notes received**: type the **Quantity** of each coin and note the
  customer gives. The **Total** must equal the amount received;
* **Notes handed back**: the quantities are proposed from the stock of the
  drawer, the largest notes first. **In the drawer** gives the stock of
  each coin and note. Change the quantities if you hand back other notes:
  the **Total** must equal the amount handed back.

A red message shows when a total does not match, and **Confirm** stays
disabled. When the drawer is short of some notes, an orange message names
them: "The drawer is short of ...: check the notes before handing them
back." It is only a warning, because the cash sales in a foreign currency
move the drawer without denominations: the stock can be behind the real
drawer. When the amount handed back cannot be made up with the coins and
notes of the currency, the popup shows it as an error.

Note Stock
----------

The **Note Stock** entry of the register menu (shown when the notes are
tracked) gives, for each tracked currency and each coin and note, the
**Opening** count, the notes moved by the **Exchanges** and the transfers,
and the stock **In the drawer**. When the opening was not counted by
coins and notes, the popup says so: the stock then counts the exchanges
only.

At closing, the counting popup of each tracked currency shows the
*expected* quantity of each coin and note next to the count, when the
opening was counted by coins and notes (or the drawer was empty at
opening).

Sending and receiving notes
---------------------------

A counter of an exchange office with another enabled counter has two more
entries in the register menu.

**Send Notes**:

1. pick the counter in **Send to**. When no register is open there, the
   popup warns that the notes stay in transit until they are received;
2. pick the currency and type the **Amount sent**. With tracked notes,
   the **Notes sent** grid proposes the notes from the stock of the drawer;
   their **Total** must equal the amount;
3. add a note if useful, then **Confirm**. The cash drawer opens and a
   transfer slip is printed: put it with the notes.

The drawer must hold the amount. The transfer gets its reference
(``TRF/YYYY/NNNNN``) and the notes leave the drawer: a cash out on the
session, on the notes in transit account of the office.

**Receive Notes** lists the notes in transit to this counter: reference,
date sent, sending counter, amount and notes. Count the notes, then press
**Receive**: the notes enter the drawer (a cash in of the same value) and
a slip is printed. When the sending counter did not count the notes by
denomination and this counter tracks them, **Receive** opens the **Notes
received** grid, prefilled with the largest notes first: correct it to the
notes really received, then press **Confirm Receipt**. **Refresh** reloads the
list.

The amount received is the amount sent. A difference shows in the closing
count of the receiving drawer.

The rate board on a screen
--------------------------

Open the **Rate board address** of the counter, or the **Rate Board
Address** of the office (button **Open Rate Board** on the office), in the
browser of the screen and put it full screen. The page shows the
currencies with **We buy**, **We sell**, **You receive for** and **You pay
for** the typical amount, the commission of each currency, the license,
the date and the time. It reloads the rates by itself. When the
connection is lost, it keeps the last rates on screen with the message
"Connection lost: last rates shown".

The board speaks the language of the company (the language of its
contact). For another language installed in the database, add it to the
address: ``&lang=fr_FR`` for French, ``&lang=de_DE`` for German, and so on.

With **Rate board on the customer display**, the customer display of Odoo
shows the board of the counter while no order is in progress.

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
* the origin of the funds is required and not declared;
* with tracked notes, the notes received or handed back do not add up to
  the amounts;
* the quote changed between the popup and the server (rate, margin or
  commission changed meanwhile): nothing is recorded, the popup shows the
  new quote at once with a warning; check it with the customer, then
  confirm again;
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
of the point of sale (100 EUR, 10,000 XPF, 1,000,000 VND), rounded to the
coins the counter takes and hands back in that currency (its Payment
Rounding and Change Rounding: 99 CHF with 3 CHF coins). The amounts are
computed by the quote of the counter, so they match the operations.
**Print** prints the board on the receipt printer.

Cancelling an operation
-----------------------

A mistaken operation is cancelled, not corrected by another operation: an
opposite operation would charge the commission again and round the notes
again, and a cash move would leave the commission on the commission
account.

A POS Administrator opens the operation (*Point of Sale → Orders →
Currency Exchanges*) and presses **Cancel Operation**, then confirms. This
is possible while the session of the operation is open and when the drawer
still holds the notes received (the customer gets them back). Two statement
lines exactly opposite to the original ones are posted on the session:
same amounts in both currencies, same counterpart account. Both drawers and
the commission account return to their state before the operation.

The operation turns **Cancelled**, with the date and the user, a message is
posted on the session and on the operation, and it no longer counts in the
commissions, the closing summary and the reports. Its receipt, reprinted,
is marked *CANCELLED*. With tracked notes, the stock of the drawer is
restored: the notes received leave it and the notes handed back return to
it (note moves *Cancellation*). The cancellation gets its own hash in the
register (**Cancellation Hash**), and an operation of a closed register
period cannot be cancelled.

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
  valid identity document: type (Passport, Identity Card, Driving License,
  Residence Permit, Other), number, issuing country, expiry date (or
  **No expiry date** for a document without one), nationality and date of
  birth. An expired document is refused.

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

*Point of Sale → Orders → Currency Exchanges* (POS Administrators) lists
the operations with their reference, date, point of sale, cashier,
customer, the notes received and handed back, the commission, the rate
margin and the status. It opens with the filter **Done**; the filter
**Cancelled** shows the cancelled ones. Other filters: *Today*, *With
Customer*, *Purchase of foreign currency*, *Sale of foreign currency*,
*Cross exchange*; group by point of sale, session, cashier, operation type,
status, currency or date. The pivot gives the commissions, rate margins and
values received per day, status and currency received; regroup it per
point of sale, session or cashier as needed.

The operation type is seen from the shop: *Purchase of foreign currency*
when it receives foreign notes, *Sale of foreign currency* when it hands
foreign notes back, *Cross exchange* between two foreign currencies.

The form of an operation shows its amounts, the **Rate Applied**
("1 USD = 119.33 XPF"), the commission, the rate margin, the identity
document and the chatter. Its buttons:

* **Send by Email** (when the operation has a customer): sends the
  receipt in PDF with the template *Currency Exchange: Send Receipt*;
* **Print**: the receipt in PDF (*Exchange Receipt*);
* **Cancel Operation** (see above);
* **Statement Lines**: the two lines of the operation, and the two lines
  of its cancellation.

Only the **Note**, **Compliance** and **Compliance Note** can be edited,
by a POS Administrator (see *To Review*); the changes of the **Note** and
of **Compliance** are logged in the chatter.

The session form has a button with the total of the commissions and
"Exchanges: N", the number of operations done; it opens them.

At an exchange office, the operation also shows its **Exchange Office**
and its **License**, and the list can be grouped by **Exchange Office**.
With tracked notes, the button **Note Moves** opens the coins and notes of
the operation.

To Review
---------

The filter **To Review** of *Currency Exchanges* gives the operations
flagged for the compliance officer: above the review threshold, or with a
politically exposed person declared. The compliance officer of the office
also gets an activity "Review the exchange operation ...".

The group **Declarations and Compliance** of the operation (POS
Administrators) shows the **Origin of Funds**, the **Origin of Funds
Details**, the **Purpose**, **Politically Exposed Person**, the **Review
Reason**, and the two fields of the review:

* **Compliance**: None, To Review, Reviewed or Reported. Set *Reviewed*
  once checked, or *Reported* when you reported the operation to the
  authorities;
* **Compliance Note**: what you checked or decided.

These two fields and the **Note** are the only ones a POS Administrator
can change; the changes of **Compliance** and of the **Note** are logged
in the chatter. The group **Identity
Document** now also shows the **Customer Address** of the operation.

Sales Details
-------------

The *Sales Details* report ends with a *Currency Exchange* table: every
operation with its session, amounts, commission and rate margin, then the
totals, one line per currency of the points of sale, and the list of the
cancelled operations, which are not counted. Printed from a session, it
covers the operations of the session; run from *Point of Sale →
Reporting → Sales Details* for a period, it covers the operations dated
in that period on the selected points of sale (all of them when none is
selected), open sessions included. The *Currency Position* report of POS
Multi-Currency Cash reflects the notes moved.

Exchange Register
-----------------

*Point of Sale → Reporting → Exchange Register* (POS Administrators)
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

The list also shows the **Origin of Funds** and the **Compliance** of each
operation; the **Exchange Office**, the **License**, the **Customer
Address**, the **Purpose**, **Politically Exposed Person** and the
**Register Hash** can be added from the optional columns. In the wizard,
pick an **Exchange Office** to print the register of its counters only.
The PDF then shows the office, its address and its license; it also gives,
for each operation, the address, nationality and date of birth of the
customer, the declarations, the compliance status and the hash.

Register integrity
------------------

Every operation is hashed (SHA-256) when it is recorded, with the hash of
the previous operation of the company: the operations form a chain. A
cancellation gets its own hash, chained to the hash of the operation. The
form of the operation shows them in the group **Register**: **Register
Hash**, **Previous Hash** and **Cancellation Hash**. Odoo refuses any
change of the hashed fields of an operation (amounts, rate, customer,
identity document, origin of funds), even by the administrator: only the
**Note** and the compliance review can still be changed.

To check the chain, press **Print Register**, then **Check Integrity**.
The check recomputes the hashes of every operation of the company, in
order:

* "N operations checked: the register is intact (last: ...)" when every
  hash matches. Operations without hash, recorded before the chain
  started, are counted apart;
* else "Integrity check failed at ...", with the first operation that
  does not match and the reason: hash missing, chain broken, the
  operation was altered, or the cancellation was altered.

The hash chain shows that an operation was changed or removed directly in
the database. It does not stop such a change, and it cannot show that the
last operations were removed: compare with the **Hash of the Last
Operation** of the last register closing, or with a printed register.

Register closings
-----------------

Close the register of a period once it is over, for instance every month:

1. *Point of Sale → Reporting → Exchange Register*, **Print Register**;
2. set **From** and **To**, and the **Exchange Office** to close the
   register of one office (leave it empty, with no point of sale, for the
   whole company);
3. press **Close Period** and confirm. The closing cannot be undone.

The register is closed only when the period is over, the sessions of its
operations are closed, it does not overlap another closing of the same
office or of the whole company (for a closing of the whole company: no
closing of one of its offices either), and the integrity check passes. The closing gets
a reference without gap (``EXR/YYYY/NNNN``) and freezes the number of
**Operations** and **Cancelled** ones, the **First Reference** and the
**Last Reference**, the **Commissions**, the **Rate Margins**, the result
of the **Integrity** check and the **Hash of the Last Operation**. The PDF
register of the period is attached: **Download Register**.

The closings are listed in *Point of Sale → Reporting → Exchange Register
Closings*. They cannot be changed or deleted, and an operation of a closed
period can no longer be cancelled.

Note Stock and Note Moves
-------------------------

*Point of Sale → Reporting → Note Stock* (POS Administrators) gives, per
session, currency and **Denomination**, the **Opening** count, the
coins and notes put **In** and taken **Out** by the operations and the
transfers, the **Stock**, the **Closing** count and the **Difference**
(closing less stock, when both counts were made by coins and notes). A
negative difference is red, a positive one orange. The filter
**Differences** keeps the lines that do not match; a pivot view gives the
stock per currency and denomination.

*Point of Sale → Reporting → Note Moves* lists every coin and note moved:
by an exchange, a cancellation or a transfer, with its session, operation
or transfer, **Denomination** and **Quantity**. The moves are never edited
nor deleted.

Note Transfers
--------------

*Point of Sale → Orders → Note Transfers* (POS Administrators) lists the
transfers with their reference, office, **From Counter**, **To Counter**,
amount, value, dates and status: Draft, In Transit, Received or Transfer
Cancelled. The filter **In Transit** gives the notes sent and not received
yet.

A POS Administrator can also make a transfer from the back office:
**New**, pick the office, the counters, the currency and the amount, then
**Send**. The sending counter needs an open session. When it tracks the
notes, the notes proposed from its stock are sent; when its stock cannot
make up the amount exactly, sending is refused ("Enter the notes sent by
denomination"): send from the register then to choose the notes. **Receive** puts the notes in the drawer of the receiving
counter, in its open session.

**Cancel** a transfer in transit while the session that sent it is open:
the notes go back to the sending drawer (a cash in on that session). A
received transfer cannot be cancelled: transfer the notes back. Once sent,
only the **Note** of a transfer can be changed. The buttons **Cash Moves**
and **Note Moves** open its statement lines and its coins and notes.

The drawers of an office
------------------------

The **Drawers** tab of the exchange office (POS Administrators) shows, for
each counter with an open session, the **Expected Cash** of every currency
(opening, sales, cash moves, exchanges and transfers), the **Operations
Today** and the **Commissions Today**, with the totals. Below, **Notes in
Transit** gives, per currency, the transfers sent and not received yet,
their amount and value, and the **Total in transit**.

Rate board in PDF
-----------------

The rate board described above is also printed in PDF (*Exchange Rates*)
with **Print Exchange Rates** in the settings, or from the *Print* menu of
the point of sale records (list view of *Point of Sale → Dashboard*).

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
* A note transfer is two statement lines too: a cash out on the session of
  the sending counter when the notes are sent, and a cash in of the same
  value on the session of the receiving counter when they are received,
  both with the **Notes in Transit Account** of the office as counterpart.
  The value is the amount at the rate of Odoo of the day, in the currency
  of the company. The balance of the account is the value of the notes in
  transit; it is back to zero once every transfer is received or
  cancelled.

Upgrading to 20.0.4.0.0
=======================

* POS Multi-Currency Cash 20.0.2.1.0 or later is still required.
* The upgrade copies the exchange license number of each point of sale on
  its existing operations, then chains the existing operations into the
  register hash, in the order of their creation, company by company. Run
  **Check Integrity** once after the upgrade.
* Nothing changes for a counter outside any exchange office: its settings
  stay as they are. The new thresholds (**Origin of funds required above**,
  **Review above**) start at 0, never applied, and **Track the notes by
  denomination** is not ticked.
* To use the offices, create them, add their counters, then set the
  **Notes in Transit Account** of each office before sending notes
  between its counters.
* Close the sessions, or reload every register, after the upgrade, so that
  the registers load the new menu entries.

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
* An operation can only be cancelled while its session is open, and not
  in a closed register period.
* The notes are tracked by denomination for the foreign currencies only:
  the currency of the point of sale has no count by coins and notes.
* The note stock follows the exchange operations and the transfers only:
  the cash sales and cash moves in a foreign currency change the drawer
  without denominations. The next count corrects it.
* A received note transfer cannot be cancelled: transfer the notes back.
* The integrity check covers the register of the whole company.

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

A rate, a margin or a commission changed after the quote: nothing was
recorded. The popup requests the new quote at once and shows it with a
warning; check the new amount with the customer, then press **Confirm**
again. The operation is never confirmed on its own.

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

Type, number and expiry date are mandatory (or **No expiry date** ticked
for a document that has none), and the document must not be expired. The
threshold may be reached with the linked operations of the customer: the
popup shows their total.

Delete is missing on the operations
-----------------------------------

The operations cannot be deleted, so that the register stays complete:
cancel the operation instead.

Send Notes and Receive Notes are missing
----------------------------------------

The counter must belong to an exchange office with at least one other
counter where **Currency Exchange** is enabled. Then reload the register.

"Set the Notes in Transit Account"
----------------------------------

Set the **Notes in Transit Account** of the exchange office (a current
assets account) before transferring notes.

The notes do not add up
-----------------------

With tracked notes, the **Total** of each grid must equal the amount of
the operation or of the transfer. Correct the quantities.

"The drawer is short of ..."
----------------------------

The stock of the drawer, as counted at opening and moved by the
operations, holds fewer of these notes. Check the notes actually handed
back or sent. It does not block the operation.

The register cannot be closed
-----------------------------

The period must be over, the sessions of its operations closed, and the
integrity check passed. It must not overlap a closing of the same office
or of the whole company; a closing of the whole company must not overlap
any closing of an office. To close the whole company, leave **Exchange Office**
and **Points of Sale** empty.

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
