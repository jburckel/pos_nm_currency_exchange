# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

from odoo.addons.pos_nm_currency_exchange import _nm_check_parent_version
from odoo.addons.pos_nm_currency_exchange.models.pos_currency_setting import nm_default_sell_margin


def migrate(cr, version):
    """20.0.2.0.0: fill the new columns before the ORM creates them, else
    they would take their default. Safe to run again.

    - The operations record the user who made them: the creator.
    - POS Multi-Currency Cash must be 20.0.2.1.0 or later.
    - The exchange sell margin of a currency starts at its cash rate margin:
      the counter now sells the notes at the rate of Odoo less this margin
      instead of plus the margin. A negative cash rate margin m handed back
      fewer notes than the rate of Odoo: the sell margin -m / (1 + m / 100)
      keeps that sell rate (2.04 % for -2 %). Same helper as the currencies
      added after the upgrade (nm_default_sell_margin).
    - The rate margin of the operations is left empty here and computed by
      the post-migration.
    """
    if not version:
        return
    _nm_check_parent_version(api.Environment(cr, SUPERUSER_ID, {}))
    cr.execute("ALTER TABLE pos_nm_exchange ADD COLUMN IF NOT EXISTS user_id int4")
    cr.execute("UPDATE pos_nm_exchange SET user_id = create_uid WHERE user_id IS NULL")
    cr.execute("ALTER TABLE pos_nm_currency_setting ADD COLUMN IF NOT EXISTS exchange_sell_margin_percent numeric")
    cr.execute("SELECT id, margin_percent FROM pos_nm_currency_setting WHERE exchange_sell_margin_percent IS NULL")
    for setting_id, margin in cr.fetchall():
        cr.execute("UPDATE pos_nm_currency_setting SET exchange_sell_margin_percent = %s WHERE id = %s",
                   [nm_default_sell_margin(float(margin or 0.0)), setting_id])
    cr.execute("ALTER TABLE pos_nm_exchange ADD COLUMN IF NOT EXISTS rate_margin numeric")
