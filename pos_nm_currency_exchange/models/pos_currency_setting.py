# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.pos_nm_multicurrencies.models.pos_currency_setting import (
    PosNmCurrencySetting as PosNmCurrencySettingBase,
)


def nm_default_sell_margin(margin_percent):
    """Exchange sell margin a currency starts from, given its cash rate
    margin ``margin_percent`` (the buy margin): the same margin, so that the
    counter earns on both sides. A negative cash rate margin m already sold
    the notes above the rate of Odoo (rate x (1 + m / 100)): the sell margin
    -m / (1 + m / 100) keeps that sell rate (2.04 % for -2 %).

    Used by the upgrade to 20.0.2.0.0 and for the currencies added since.
    A cash rate margin of -100 % or less is refused by POS Multi-Currency
    Cash: 0 is returned for it, so that its constraint gives the error.
    """
    margin = margin_percent or 0.0
    if margin <= -100:
        return 0.0
    if margin < 0:
        return -margin / (1 + margin / 100.0)
    return margin


class PosNmCurrencySetting(models.Model):
    _inherit = 'pos.nm.currency.setting'

    company_currency_id = fields.Many2one(related='config_id.currency_id', string='Company Currency')
    exchange_sell_margin_percent = fields.Float(
        string='Exchange Sell Margin (%)',
        digits=(16, 4),
        help='Margin of the exchange counter on the notes of this currency it hands back, with the '
             'rate of Odoo: they are handed back at the rate of Odoo divided by 1 + this margin, '
             'so the counter sells them above the market. The notes received keep the cash rate '
             '(the rate of Odoo with the Cash Rate Margin, the buy margin). A new currency starts '
             'from its Cash Rate Margin (a negative Cash Rate Margin m gives -m / (1 + m / 100), '
             'which keeps its sell rate: 2.04 for -2), as the currencies upgraded from 20.0.1; '
             'change it afterwards. With a fixed cash rate, the notes are handed back at the lower '
             'of the fixed rate and the fixed change rate, and this margin is not used.',
    )
    exchange_commission_percent = fields.Float(
        string='Exchange Commission (%)',
        digits=(16, 4),
        help='Commission of an exchange operation involving this currency, in percent of the '
             'value of the notes received, converted to the currency of the point of sale.',
    )
    exchange_commission_fixed = fields.Monetary(
        string='Fixed Exchange Commission',
        currency_field='company_currency_id',
        help='Fixed commission of an exchange operation involving this currency, in the '
             'currency of the point of sale, added to the percentage.',
    )
    exchange_commission_min = fields.Monetary(
        string='Minimum Exchange Commission',
        currency_field='company_currency_id',
        help='Minimum commission of an exchange operation involving this currency, in the '
             'currency of the point of sale.',
    )

    # Logged in the chatter like the rates: the fields of the parent module
    # plus the sell margin and the commissions.
    _NM_LOGGED_FIELDS = PosNmCurrencySettingBase._NM_LOGGED_FIELDS + (
        'exchange_sell_margin_percent', 'exchange_commission_percent', 'exchange_commission_fixed',
        'exchange_commission_min')

    @api.model_create_multi
    def create(self, vals_list):
        """A currency added without an exchange sell margin starts from its
        cash rate margin (nm_default_sell_margin), like the currencies of
        the upgrade, instead of selling its notes at the rate of Odoo."""
        if 'default_exchange_sell_margin_percent' not in self.env.context:
            default_margin = None
            for vals in vals_list:
                if 'exchange_sell_margin_percent' in vals:
                    continue
                if 'margin_percent' in vals:
                    margin = vals['margin_percent']
                else:
                    if default_margin is None:
                        default_margin = self.default_get(['margin_percent']).get('margin_percent') or 0.0
                    margin = default_margin
                vals['exchange_sell_margin_percent'] = nm_default_sell_margin(margin)
        return super().create(vals_list)

    @api.onchange('margin_percent')
    def _onchange_margin_percent_sell_margin(self):
        """A currency being added follows its cash rate margin until it is
        saved; the sell margin of a saved currency is never changed."""
        for setting in self.filtered(lambda s: not s._origin):
            setting.exchange_sell_margin_percent = nm_default_sell_margin(setting.margin_percent)

    @api.constrains('exchange_sell_margin_percent', 'exchange_commission_percent', 'exchange_commission_fixed',
                    'exchange_commission_min')
    def _check_exchange_commission(self):
        for setting in self:
            if setting.exchange_commission_percent < 0 or setting.exchange_commission_fixed < 0 \
               or setting.exchange_commission_min < 0:
                raise ValidationError(_("The exchange commissions cannot be negative."))
            if setting.exchange_sell_margin_percent < 0:
                raise ValidationError(_("The exchange sell margin cannot be negative."))
            if setting.exchange_commission_percent >= 100:
                raise ValidationError(_("The exchange commission must be lower than 100%."))

    def _nm_exchange_commission(self, value):
        """Commission on an operation worth ``value`` in the currency of the
        point of sale: percentage plus fixed part, at least the minimum."""
        self.ensure_one()
        currency = self.company_currency_id
        commission = value * self.exchange_commission_percent / 100.0 + self.exchange_commission_fixed
        return currency.round(max(commission, self.exchange_commission_min))
