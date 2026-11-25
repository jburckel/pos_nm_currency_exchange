# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.pos_nm_multicurrencies.models.pos_currency_setting import (
    PosNmCurrencySetting as PosNmCurrencySettingBase,
)


class PosNmCurrencySetting(models.Model):
    _inherit = 'pos.nm.currency.setting'

    company_currency_id = fields.Many2one(related='config_id.currency_id', string='Company Currency')
    exchange_sell_margin_percent = fields.Float(
        string='Exchange Sell Margin (%)',
        digits=(16, 4),
        default=0.0,
        help='Margin of the exchange counter on the notes of this currency it hands back, with the '
             'rate of Odoo: they are handed back at the rate of Odoo divided by 1 + this margin, '
             'so the counter sells them above the market. The notes received keep the cash rate '
             '(the rate of Odoo with the Cash Rate Margin, the buy margin). With a fixed cash '
             'rate, the notes are handed back at the lower of the fixed rate and the fixed change '
             'rate, and this margin is not used.',
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
