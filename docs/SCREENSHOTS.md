# Screenshots of the store page (20.0)

The screenshots of `pos_nm_currency_exchange/static/description/` are captured on the
same demo database as the parent module (`shots`, see `docs/SCREENSHOTS.md` of
`pos_nm_multicurrencies`), without a graphical browser. Everything needed to redo them
is under `tools/screenshots/`.

## Recipe

1. **Database**: the `shots` database of the parent module (demo data, Riverside
   Boutique, EUR and GBP on the cash method, an open session), then
   `odoo-bin -c odoo.conf -d shots -i pos_nm_currency_exchange --stop-after-init`.
   The server runs in the background on port 8069 (`--log-level=warn`); stop it
   (`pkill -f "http-port=806[9]"`) before running a test suite, the tours bind the
   same port.
2. **Data**: `odoo-bin shell -c odoo.conf -d shots --no-http < tools/screenshots/shots_data.py`
   enables the counter on the point of sale with the Other Income account, a customer
   required above 250, an identity document above 400 with 7 days of linked operations,
   the licence number and a receipt header and footer; sets the sell margin of EUR (2 %)
   and the commissions of EUR (2 % + 1, minimum 3) and GBP (1.5 %, minimum 2); gives
   Olivia Bennett a passport; opens the session with the counts the opening popup
   proposes (main-currency notes only, no opening difference) and a cash in of 1,000 to
   the main drawer; records six operations (USD to EUR with a customer, GBP to USD, EUR
   to USD with a customer, USD to GBP, EUR to USD for Olivia Bennett with her passport,
   USD to EUR) and cancels the last one. It then sets up the exchange office of
   20.0.4.0.0: the *Riverside Exchange Office* (address and license of the company,
   Mitchell Admin as compliance officer, a *Notes in Transit* current asset account
   101098, the same customer, identity document and linked operations rules as the
   point of sale, origin of funds required above 1,000, review above 1,500), coins of
   1 and 2 for EUR and GBP next to the notes, a second counter *Riverside Counter 2*
   (copy of the point of sale with its own cash journal `CTR2` and cash payment method
   in EUR and GBP, *Track the Notes by Denomination* ticked), both counters in the
   office with the first one as reference counter and *Apply Rates to the Counters*
   (rate sync, no rate difference left); opens Counter 2 with EUR and GBP counted by
   denomination (1,080 EUR, 580 GBP) and a cash in of 3,000; records four operations
   there with their notes (USD to EUR, GBP to EUR, GBP to USD, and 1,800 EUR to USD for
   Daniel Moreau with his passport and his declarations: origin of funds, purpose,
   flagged *To Review* with an activity of the compliance officer); sends 500 EUR
   (3 x 100, 4 x 50) from Counter 2 to the first counter, left *In Transit*. It ends
   with `env.cr.commit()` and prints the ids (lines `IDS` and `IDS2`). Run it once on
   a fresh copy of the database: the captures record one more operation (the popup is
   confirmed), so start again from a copy to redo them (`createdb -O <odoo user> -T
   <copy> shots`: a database owned by another role is not listed by Odoo).
3. **Captures**: `python tools/screenshots/shots_capture.py <config_id> <session_id>
   <eur_setting_id> <cancelled_id> <office_id> <config2_id> <review_id> <transfer_id>`
   (the last four from the line `IDS2`; without them only the captures of 20.0.3 are
   taken) with Playwright for Python (`pip install playwright`
   in a virtualenv, no `playwright install` needed) and the headless Chromium of
   `$CHROME` (default `/usr/local/bin/chromium`), viewport 1440 x 900, login admin on
   `/web/login`.
   - back-office by action URL (`/odoo/action-<xmlid>`, `?view_type=pivot`,
     `/odoo/action-<xmlid>/<id>` for a form); the list and the pivot at 1680 px wide
     (every column at full width); the settings block is a clip of the heading and its
     container; the currency setting form is its `.o_form_sheet`; the cancelled
     operation is its `.o_form_renderer` (form and chatter); the report blocks are the
     `#nm_exchange` element of the Sales Details report and the `.page` of the Exchange
     Register report of the month (`/report/html/...?options=` with the dates) and
     the `.page` of the Exchange Rates report of the point of sale
     (`/report/html/pos_nm_currency_exchange.report_exchange_rates/<config_id>`,
     1200 px wide, with a white padding added around the page);
   - register: `/pos/ui/<config_id>?from_backend=True`, `printWithFallback` of the
     ticket printer replaced to keep the receipt frame, burger menu > Currency
     Exchange, USD to EUR, 100 typed, popup captured as `.modal-content`, Confirm,
     then the receipt shown from `#receipt-iframe-container`; burger menu > Exchange
     Rates for the rate board; Currency Exchange again, 300 EUR to USD for Olivia
     Bennett (linked operations above the threshold: the identity document is asked),
     Discard; then burger menu > Close Register in a 1600 px high viewport for the
     closing popup, clipped down to its Currency Exchange block;
   - exchange office, in a 1500 px high viewport (the whole sheet without
     scrolling): the office form
     (`/odoo/action-pos_nm_currency_exchange.action_pos_nm_exchange_office/<office_id>`)
     as its `.o_form_renderer` (form and chatter), its *Drawers* page as the
     `.o_notebook`, the address of the board read on the *Rate Board* page; the
     operation flagged To Review
     (`/odoo/action-pos_nm_currency_exchange.action_pos_nm_exchange_register/<review_id>`)
     as its `.o_form_sheet`; the rate board of the office opened at that address in a
     page of 1280 x 720 (full screen, no login);
   - register of Counter 2 (`/pos/ui/<config2_id>?from_backend=True`) in a 1600 px
     high viewport (the grids of notes without scrolling): burger menu > Currency
     Exchange, 100 GBP to EUR, notes received typed (1 x 50, 2 x 20, 1 x 10), the
     notes handed back as proposed from the stock, popup captured, Discard; burger
     menu > Note Stock; burger menu > Send Notes, 200 EUR to Riverside Boutique with
     the notes proposed from the stock, Discard.
4. **Assembly**: `python tools/screenshots/shots_assemble.py <raw captures dir>` writes
   `static/description/screenshot_exchange_<subject>.png`: the popups and the receipt
   are placed on a neutral background of the ratio of their row (the two images of a
   row must share their ratio, or the headings under them are not aligned), the list,
   the pivot and the cancelled operation keep only the top of the screen, the rate
   board in PDF is framed alone at full width; the office form keeps the top of the
   screen, the Drawers page is framed alone, the exchange popup with its notes beside
   the note stock and Send Notes beside the operation To Review share the ratio of
   their row, and the rate board of the office stays at 1280 x 720. Never run it
   on `static/description` itself. The files are referenced in `index.html` and in the
   `images` key of the manifest, after `banner.png`.

## Banner and icon

`tools/make_banner.js` renders `banner.png` (1200 x 600) from `tools/banner.html`:
see the *Banner* section of the README. Its card carries the figures of
`screenshot_exchange_popup.png`, the first screenshot of the page and of the
manifest: change them together. `tools/branding/build_branding.py` renders
`icon.png` (512 x 512) with headless Chrome. The first image of the manifest is
the banner of the store page.

## Store page layout

The Odoo Apps Store frames `oe_screenshot` images with a capped height and drops the
`gap` of flex containers: `index.html` uses Bootstrap rows (`row`, `col-md-6`, padded
columns), frames drawn with inline styles, and images at `width: 100%`.

## Files

| File | Subject | Where it is taken |
| --- | --- | --- |
| `screenshot_exchange_settings.png` | *Currency Exchange* section of the Point of Sale settings | `/odoo/action-point_of_sale.action_pos_configuration`, clip of the block |
| `screenshot_exchange_commissions.png` | Cash currency setting of EUR with the Currency Exchange group | `/odoo/action-pos_nm_multicurrencies.action_pos_nm_currency_setting/<id>` |
| `screenshot_exchange_list.png` | Currency Exchanges list | `/odoo/action-pos_nm_currency_exchange.action_pos_nm_exchange` |
| `screenshot_exchange_pivot.png` | Pivot of the commissions per currency | same action, `?view_type=pivot` |
| `screenshot_exchange_sale_details.png` | Currency Exchange block of the Sales Details report | `/report/html/point_of_sale.report_saledetails/<session_id>`, `#nm_exchange` |
| `screenshot_exchange_popup.png` | Exchange popup with the quote (100 USD to EUR) | register, burger menu > Currency Exchange |
| `screenshot_exchange_receipt.png` | Exchange receipt | register, receipt frame after Confirm |
| `screenshot_exchange_closing.png` | Closing register with the operations in the moves of each currency | register, burger menu > Close Register |
| `screenshot_exchange_rates.png` | Rate board of the counter (We buy, You receive, We sell, You pay, Commission) | register, burger menu > Exchange Rates |
| `screenshot_exchange_rates_pdf.png` | Rate board in PDF (*Exchange Rates* report of the point of sale) | `/report/html/pos_nm_currency_exchange.report_exchange_rates/<config_id>`, `.page` |
| `screenshot_exchange_document.png` | Exchange popup asking the identity document (300 EUR to USD, linked operations of Olivia Bennett) | register, burger menu > Currency Exchange, customer selected |
| `screenshot_exchange_cancelled.png` | Cancelled operation: status, warning, cancellation in the chatter | `/odoo/action-pos_nm_currency_exchange.action_pos_nm_exchange/<cancelled_id>` |
| `screenshot_exchange_register.png` | Exchange Register of the month with the identity document and the totals per currency | `/report/html/pos_nm_currency_exchange.report_exchange_register?options=...`, `.page` |
| `screenshot_exchange_office.png` | Exchange office: rules of the counters, notes in transit account, compliance officer, the two counters and the reference counter, rates applied in the chatter | `/odoo/action-pos_nm_currency_exchange.action_pos_nm_exchange_office/<office_id>` |
| `screenshot_exchange_drawers.png` | *Drawers* page of the office: expected cash of the two open counters, operations and commissions of the day, notes in transit | same form, *Drawers* page |
| `screenshot_rate_board_display.png` | Rate board of the office for a screen facing the customers (1280 x 720) | `/pos_nm_exchange/office_board/<office_id>?access_token=...` |
| `screenshot_exchange_notes.png` | Exchange popup with the notes received and the notes handed back by denomination (100 GBP to EUR) | register of Counter 2, burger menu > Currency Exchange |
| `screenshot_note_stock.png` | Note Stock of the EUR and GBP drawers (opening, exchanges, in the drawer) | register of Counter 2, burger menu > Note Stock |
| `screenshot_note_transfer.png` | Send Notes: 200 EUR to the other counter, notes sent by denomination | register of Counter 2, burger menu > Send Notes |
| `screenshot_exchange_compliance.png` | Operation flagged To Review: identity document, declarations, review reason, register hash | `/odoo/action-pos_nm_currency_exchange.action_pos_nm_exchange_register/<review_id>` |
