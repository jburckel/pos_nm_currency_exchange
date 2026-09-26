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
   enables the counter on the point of sale with the Other Income account and a
   500 threshold, sets the commissions of EUR (2 % + 1, minimum 3) and GBP (1.5 %,
   minimum 2), opens the session with counts if needed and records four operations
   (USD to EUR with a customer, GBP to USD, EUR to USD with a customer, USD to GBP).
   It ends with `env.cr.commit()` and prints the ids.
3. **Captures**: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python tools/screenshots/shots_capture.py
   <config_id> <session_id> <eur_setting_id>` with Playwright and the headless Chromium
   of `/opt/pw-browsers/chromium-*/chrome-linux/chrome`, viewport 1440 x 900, login
   admin on `/web/login`.
   - back-office by action URL (`/odoo/action-<xmlid>`, `?view_type=pivot`,
     `/odoo/action-<xmlid>/<id>` for a form); the settings block is a clip of the
     heading and its container; the currency setting form is its `.o_form_sheet`;
     the report block is the `#nm_exchange` element of the HTML report;
   - register: `/pos/ui/<config_id>?from_backend=True`, `printWithFallback` of the
     ticket printer replaced to keep the receipt frame, burger menu > Currency
     Exchange, USD to EUR, 100 typed, popup captured as `.modal-content`, Confirm,
     then the receipt shown from `#receipt-iframe-container`, then burger menu >
     Close Register for the closing popup.
4. **Assembly**: `python tools/screenshots/shots_assemble.py <raw captures dir>` writes
   `static/description/screenshot_exchange_<subject>.png`: the popups and the receipt
   are placed on a neutral background of the ratio of their row (the two images of a
   row must share their ratio, or the headings under them are not aligned), the list
   and pivot keep only the top of the screen. Never run it on `static/description`
   itself. The files are referenced in `index.html` and in the `images` key of the
   manifest, after `banner.png`.

## Banner and icon

`tools/branding/build_branding.py` renders `banner.png` (1440 x 600) and `icon.png`
(512 x 512) with headless Chrome, in the style of `pos_nm_multicurrencies` (blue
gradient, faded currency symbols, white Open Sans text). The first image of the
manifest is the banner of the store page.

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
