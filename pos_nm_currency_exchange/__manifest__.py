# -*- coding: utf-8 -*-
{
    "name": "POS Currency Exchange",
    "summary": "Currency exchange counter at the Point of Sale: buy and sell foreign notes with a commission, receipt, rate board and exchange register, on the drawers of POS Multi-Currency Cash",
    "description": """
POS Currency Exchange
=====================

A currency exchange counter inside the Odoo Point of Sale: the customer
brings notes in one currency and leaves with another, without buying a
product. Built on POS Multi-Currency Cash, which already controls the
drawer of every currency, its cash rates and coins and notes.

Features
--------
* Exchange operation from the menu of the register, between any two cash
  currencies of the point of sale: type the amount received, or the amount
  the customer wants handed back
* Buy and sell rates: notes received at the cash rate of POS Multi-Currency
  Cash, notes handed back at a sell rate with its own margin, always in
  favour of the shop; rate margin of every operation at the rates of Odoo
* Commission per currency: percentage, fixed part and minimum; the notes
  handed back are rounded down to the coins and notes of their currency
  (cash rounding of the point of sale for its own currency), the remainder
  stays in the commission
* Drawer of the currency handed back checked before every operation
* Exchange receipt with the header and footer of the point of sale and the
  exchange licence number; reprint from the register, PDF and e-mail from
  the back office
* Rate board of the counter: on the register, printed on the receipt
  printer or in PDF
* Customer identification: thresholds, linked operations over a period,
  identity document recorded on the operation
* Cancellation of an operation by a manager while its session is open: two
  opposite lines, drawers and commission account back to their state;
  operations cannot be edited or deleted, references are gapless
* Two lines on the cash journal of the session, in the currency of each
  side, with the commission on a dedicated income account: the operations
  appear in the closing control, the Currency Position report and the Sales
  Details report
* Exchange offices: several counters sharing a licence, identification
  rules and the same rates, applied from a reference counter
* Compliance: origin of funds and review thresholds, politically exposed
  person, review by the compliance officer; inalterable register (hash
  chain, integrity check) and closings of the register per period
* Rate board on a screen facing the customers (TV, tablet or the customer
  display of Odoo), refreshed by itself
* Operations listed per point of sale, session and cashier, with a pivot of
  the commissions and rate margins; exchange register exported to Excel or
  printed in PDF for a period

Requirements
------------
* Point of Sale (point_of_sale)
* POS Multi-Currency Cash (pos_nm_multicurrencies) 20.0.2.1.0 or later,
  included in the price shown on the Odoo Apps Store (already bought it?
  Contact us at odoo@natimai.solutions before buying this module)
    """,
    "version": "20.0.3.0.0",
    "category": "Sales/Point of Sale",
    "author": "Natimai Solutions",
    "website": "https://www.natimai.solutions",
    "license": "OPL-1",
    "support": "odoo@natimai.solutions",
    "application": False,
    "installable": True,
    "auto_install": False,
    "depends": ["pos_nm_multicurrencies"],
    "pre_init_hook": "pre_init_hook",
    "data": [
        "security/ir.access.csv",
        "data/ir_sequence_data.xml",
        "receipt/pos_exchange_receipt.xml",
        "report/pos_exchange_reports.xml",
        "data/mail_template_data.xml",
        "wizard/pos_exchange_register_wizard.xml",
        "views/pos_exchange_views.xml",
        "views/pos_currency_setting_views.xml",
        "views/pos_session_views.xml",
        "views/res_config_settings.xml",
        "views/res_partner_views.xml",
        "views/pos_exchange_office_views.xml",
        "views/pos_nm_note_stock_views.xml",
        "views/rate_board_templates.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_nm_currency_exchange/static/src/**/*",
            ("remove", "pos_nm_currency_exchange/static/src/customer_display_board/**/*"),
        ],
        "point_of_sale.customer_display_assets": [
            "pos_nm_currency_exchange/static/src/customer_display_board/**/*",
        ],
        "web.assets_tests": [
            "pos_nm_currency_exchange/static/tests/tours/**/*",
        ],
    },
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_exchange_popup.png",
        "static/description/screenshot_exchange_receipt.png",
        "static/description/screenshot_exchange_closing.png",
        "static/description/screenshot_exchange_document.png",
        "static/description/screenshot_exchange_rates.png",
        "static/description/screenshot_exchange_rates_pdf.png",
        "static/description/screenshot_exchange_cancelled.png",
        "static/description/screenshot_exchange_commissions.png",
        "static/description/screenshot_exchange_list.png",
        "static/description/screenshot_exchange_pivot.png",
        "static/description/screenshot_exchange_sale_details.png",
        "static/description/screenshot_exchange_register.png",
        "static/description/screenshot_exchange_settings.png",
    ],
    "price": 59.00,
    "currency": "EUR",
}
