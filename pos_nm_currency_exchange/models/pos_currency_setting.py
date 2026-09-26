# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosNmCurrencySetting(models.Model):
    _inherit = 'pos.nm.currency.setting'

    company_currency_id = fields.Many2one(related='config_id.currency_id', string='Company Currency')
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

    _NM_LOGGED_FIELDS = ('rate_mode', 'fixed_rate', 'fixed_change_rate', 'margin_percent',
                         'exchange_commission_percent', 'exchange_commission_fixed', 'exchange_commission_min')

    @api.constrains('exchange_commission_percent', 'exchange_commission_fixed', 'exchange_commission_min')
    def _check_exchange_commission(self):
        for setting in self:
            if setting.exchange_commission_percent < 0 or setting.exchange_commission_fixed < 0 \
               or setting.exchange_commission_min < 0:
                raise ValidationError(_("The exchange commissions cannot be negative."))
            if setting.exchange_commission_percent >= 100:
                raise ValidationError(_("The exchange commission must be lower than 100%."))

    def _nm_exchange_commission(self, value):
        """Commission on an operation worth ``value`` in the currency of the
        point of sale: percentage plus fixed part, at least the minimum."""
        self.ensure_one()
        currency = self.company_currency_id
        commission = value * self.exchange_commission_percent / 100.0 + self.exchange_commission_fixed
        return currency.round(max(commission, self.exchange_commission_min))
