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

Planned for the first version
-----------------------------
* Buy and sell operation from the register menu, in any cash currency of
  the point of sale
* Commission per currency, fixed or in percent, with a minimum
* Exchange receipt for the customer
* Entries on the cash journal in both currencies, visible in the closing
  control, the Currency Position report and the session report
* Identification of the customer above a threshold

Requirements
------------
* Point of Sale (point_of_sale)
* POS Multi-Currency Cash (pos_nm_multicurrencies) 20.0
    """,
    "version": "20.0.0.1.0",
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
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_nm_currency_exchange/static/src/**/*",
        ],
    },
    "images": [],
}
