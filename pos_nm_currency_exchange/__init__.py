# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tools import parse_version

from . import controllers
from . import models
from . import wizard

# The register imports the coin helpers of this version of POS
# Multi-Currency Cash: with an older one, the whole register fails to load.
PARENT_MIN_VERSION = '20.0.2.1.0'


def _nm_check_parent_version(env):
    """Refuse to install or upgrade on an older POS Multi-Currency Cash."""
    env.cr.execute("SELECT latest_version FROM ir_module_module WHERE name = 'pos_nm_multicurrencies'")
    row = env.cr.fetchone()
    if not row or not row[0] or parse_version(row[0]) < parse_version(PARENT_MIN_VERSION):
        raise UserError(env._(
            "POS Multi-Currency Cash %(version)s or later is required: update it first (installed: %(installed)s).",
            version=PARENT_MIN_VERSION, installed=(row and row[0]) or '-'))


def pre_init_hook(env):
    _nm_check_parent_version(env)
