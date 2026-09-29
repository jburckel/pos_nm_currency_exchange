# -*- coding: utf-8 -*-
{
    "name": "POS Currency Exchange",
    "summary": "Currency exchange counter at the Point of Sale: buy and sell foreign notes with a commission, on the drawers of POS Multi-Currency Cash",
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
  currencies of the point of sale (the notes received and the notes handed
  back), at the cash rates of POS Multi-Currency Cash
* Commission per currency: percentage, fixed part and minimum; the notes
  handed back are rounded to the coins and notes of their currency, the
  remainder stays in the commission
* Exchange receipt printed for the customer
* Two lines on the cash journal of the session, in the currency of each
  side, with the commission on a dedicated income account: the operations
  appear in the closing control, the Currency Position report and the
  session report
* Identification of the customer above a threshold
* Operations listed per point of sale, session and cashier, with a pivot of
  the commissions

Requirements
------------
* Point of Sale (point_of_sale)
* POS Multi-Currency Cash (pos_nm_multicurrencies) 20.0
    """,
    "version": "20.0.1.1.0",
    "category": "Sales/Point of Sale",
    "author": "Natimai Solutions",
    "website": "https://www.natimai.solutions",
    "license": "OPL-1",
    "support": "odoo@natimai.solutions",
    "application": False,
    "installable": True,
    "auto_install": False,
    "depends": ["pos_nm_multicurrencies"],
    "data": [
        "security/ir.access.csv",
        "data/ir_sequence_data.xml",
        "views/pos_exchange_views.xml",
        "views/pos_currency_setting_views.xml",
        "views/pos_session_views.xml",
        "views/res_config_settings.xml",
        "receipt/pos_exchange_receipt.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_nm_currency_exchange/static/src/**/*",
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
        "static/description/screenshot_exchange_commissions.png",
        "static/description/screenshot_exchange_list.png",
        "static/description/screenshot_exchange_pivot.png",
        "static/description/screenshot_exchange_sale_details.png",
        "static/description/screenshot_exchange_settings.png",
    ],
    "price": 59.00,
    "currency": "EUR",
}
