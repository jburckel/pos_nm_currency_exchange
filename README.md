# pos_nm_currency_exchange

Odoo 20 module: a currency exchange counter inside the Point of Sale, built on
[`pos_nm_multicurrencies`](https://github.com/jburckel/pos_nm_multicurrencies)
(POS Multi-Currency Cash), which controls the cash drawer of every currency.

## Layout

- [`pos_nm_currency_exchange/`](pos_nm_currency_exchange/) — the Odoo module (this
  directory is what gets packaged)
- [`pos_nm_currency_exchange/doc/`](pos_nm_currency_exchange/doc/) — the user guide
  (RST, rendered to PDF under `static/description/`)
- [`pos_nm_currency_exchange/CHANGELOG.md`](pos_nm_currency_exchange/CHANGELOG.md)
- [`tools/`](tools/) — build tooling (not shipped): documentation PDFs, the
  banner and the screenshot scripts of the store page
- [`docs/`](docs/) — maintainer notes (design, screenshot recipe)

## Branches

`20.0` is the first and main branch: the module needs `pos_nm_multicurrencies`
20.0.2.1.0 or later and the native foreign-currency cash payments of Odoo 20.

## Status

Version 20.0.4.0.0: exchange operation from the register menu between any two
cash currencies of the point of sale, with a reverse quote (amount handed back
typed, amount to receive computed) and the balance of the drawer; buy rate (cash
rate of the parent) and sell rate (Exchange Sell Margin) in favour of the shop,
rate margin of every operation; commission per currency (percentage, fixed part,
minimum) with the notes handed back rounded down to the coins (cash rounding of
the point of sale for its own currency); drawer check in every currency;
receipt with the header and footer of the point of sale and the license number,
reprint, PDF and email; rate board (register, receipt printer, PDF); customer
identification with thresholds, linked operations and identity document;
cancellation by a POS Administrator while the session is open and the drawer
still holds the notes received, read-only operations (only the note editable by
a POS Administrator), gapless references; exchange register (list, Excel, PDF per period); closing
control, Currency Position and Sales Details.

New in 20.0.4.0.0, the exchange office vertical (lots 1-5 of
[`docs/PLAN_EXCHANGE_OFFICE.md`](docs/PLAN_EXCHANGE_OFFICE.md)): exchange
offices with counters sharing a license, identification rules and the rates of
a reference counter; compliance (origin of funds and review thresholds,
politically exposed person, review by the compliance officer); inalterable
register (hash chain, integrity check, register closings per period); rate board
for the customers (public page per counter and per office, idle screen of the
customer display); note stock by denomination (note moves, Note Stock report,
expected quantities at closing); note transfers between the counters of an
office through a notes in transit account, with the drawers of every counter on
the office. See
[`pos_nm_currency_exchange/CHANGELOG.md`](pos_nm_currency_exchange/CHANGELOG.md)
and [`docs/DESIGN.md`](docs/DESIGN.md).

## Tooling

### Documentation PDFs

```
pip install docutils
python tools/build_doc_pdf.py          # all languages
```

Same chain as the parent module: docutils (RST to HTML, `tools/doc_pdf.css`
embedded) then headless Chrome (HTML to PDF). Set `CHROME=<path>` when Chrome is
not in the usual places.

### Translations

`i18n/pos_nm_currency_exchange.pot` is exported by Odoo from a database where
the module is up to date (a config file giving the database and the addons path):

```
odoo-bin -c <config> -u pos_nm_currency_exchange --stop-after-init
odoo-bin i18n export -c <config> pos_nm_currency_exchange -o pos_nm_currency_exchange/i18n/pos_nm_currency_exchange.pot
```

`fr.po`, `de.po`, `es.po` and `en.po` follow the template entry for entry, every
message translated; check them with `msgfmt -c --statistics -o /dev/null <file>`.
The UI terms of the guides (`doc/index_<lang>.rst`) are the translations of the
interface, of this module and of POS Multi-Currency Cash.

### Screenshots

See [`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md): a demo database with both
modules, `tools/screenshots/shots_data.py` through `odoo-bin shell`, then
`tools/screenshots/shots_capture.py` with Playwright.

### Banner

`pos_nm_currency_exchange/static/description/banner.png`, the first picture of
the store page and of its gallery, is rendered from `tools/banner.html`,
1200 x 600. The size is not free: the cover at the top of the module page on
apps.odoo.com is a CSS background in a 2:1 frame (`background-size: cover`),
which crops any other ratio at the centre - a 1440 x 600 picture loses about
120 px on each side there:

```
NODE_PATH=$(npm root -g) node tools/make_banner.js
```

Playwright with headless Chromium, viewport and clip 1200 x 600, device scale
factor 1; the Inter font must be installed. The description shows the picture
about 780 px wide: no text of `tools/banner.html` is under 18 px. Its card
carries the figures of the exchange popup (`screenshot_exchange_popup.png`),
without the Rate line: change them together when the demo data changes.

### Tests

On a database holding `pos_nm_multicurrencies` and this module:

```
odoo-bin -d <database> -u pos_nm_currency_exchange --test-tags /pos_nm_currency_exchange --stop-after-init
```

## License & support

- License: OPL-1 (see [`pos_nm_currency_exchange/LICENSE`](pos_nm_currency_exchange/LICENSE))
- Author: [Natimai Solutions](https://www.natimai.solutions)
- Support: odoo@natimai.solutions
