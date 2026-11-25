# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# Also set on the field of the settings: a related field does not copy the
# domain of its target.
EXCHANGE_INCOME_ACCOUNT_DOMAIN = [('account_type', 'in', ('income', 'income_other'))]


class PosConfig(models.Model):
    _inherit = 'pos.config'

    nm_exchange_enabled = fields.Boolean(
        string='Currency Exchange',
        default=True,
        help='Offer the currency exchange counter in the menu of the register: the customer '
             'brings notes in one cash currency of the point of sale and leaves with another.',
    )
    nm_exchange_income_account_id = fields.Many2one(
        'account.account',
        string='Exchange Commission Account',
        check_company=True,
        domain=EXCHANGE_INCOME_ACCOUNT_DOMAIN,
        help='Income account receiving the commissions of the exchange operations.',
    )
    nm_exchange_customer_threshold = fields.Monetary(
        string='Exchange Customer Required Above',
        currency_field='currency_id',
        help='Value of an exchange operation, in the currency of the point of sale, above which '
             'the customer must be identified. 0: never required.',
    )
    nm_exchange_count = fields.Integer(string='Exchanges', compute='_compute_nm_exchange_count')

    def _compute_nm_exchange_count(self):
        counts = dict(self.env['pos.nm.exchange']._read_group(
            [('config_id', 'in', self.ids), ('state', '=', 'done')], ['config_id'], ['__count']))
        for config in self:
            config.nm_exchange_count = counts.get(config, 0)

    @api.constrains('nm_exchange_customer_threshold')
    def _check_nm_exchange_customer_threshold(self):
        for config in self:
            if config.nm_exchange_customer_threshold < 0:
                raise ValidationError(_("The identification threshold cannot be negative."))

    @api.constrains('nm_exchange_income_account_id')
    def _check_nm_exchange_income_account(self):
        for config in self:
            account = config.nm_exchange_income_account_id
            if account and account.account_type not in ('income', 'income_other'):
                raise ValidationError(_("The exchange commission account must be an income account."))

    def _nm_exchange_currencies(self):
        """Currencies of the exchange counter: the currency of the point of
        sale and the foreign currencies of its cash payment method."""
        self.ensure_one()
        return self.currency_id | self._nm_get_foreign_cash_currencies()

    def action_nm_view_exchanges(self):
        self.ensure_one()
        return {
            'name': _('Currency Exchanges'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.nm.exchange',
            'view_mode': 'list,form,pivot',
            'domain': [('config_id', '=', self.id)],
            # Like the count of the button: the cancelled operations are
            # one filter away.
            'context': {'default_config_id': self.id, 'search_default_done': 1},
        }
