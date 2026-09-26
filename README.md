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
- [`tools/`](tools/) — build tooling (not shipped): documentation PDFs and the
  screenshot scripts of the store page
- [`docs/`](docs/) — maintainer notes (design, screenshot recipe)

## Branches

`20.0` is the first and main branch: the module needs `pos_nm_multicurrencies`
20.0 and the native foreign-currency cash payments of Odoo 20.

## Status

Version 20.0.1.0.0: exchange operation from the register menu between any two
cash currencies of the point of sale, commission per currency (percentage,
fixed part, minimum), exchange receipt, two statement lines on the cash journal
of the session visible in the closing control, the Currency Position report
and the session report, identification of the customer above a threshold,
list and pivot of the operations. See
[`pos_nm_currency_exchange/CHANGELOG.md`](pos_nm_currency_exchange/CHANGELOG.md).

## Tooling

### Documentation PDFs

```
pip install docutils
python tools/build_doc_pdf.py          # all languages
```

Same chain as the parent module: docutils (RST to HTML, `tools/doc_pdf.css`
embedded) then headless Chrome (HTML to PDF). Set `CHROME=<path>` when Chrome is
not in the usual places.

### Screenshots

See [`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md): a demo database with both
modules, `tools/screenshots/shots_data.py` through `odoo-bin shell`, then
`tools/screenshots/shots_capture.py` with Playwright.

### Tests

On a database holding `pos_nm_multicurrencies` and this module:

```
odoo-bin -d <database> -u pos_nm_currency_exchange --test-tags /pos_nm_currency_exchange --stop-after-init
```

## License & support

- License: OPL-1 (see [`pos_nm_currency_exchange/LICENSE`](pos_nm_currency_exchange/LICENSE))
- Author: [Natimai Solutions](https://www.natimai.solutions)
- Support: odoo@natimai.solutions
