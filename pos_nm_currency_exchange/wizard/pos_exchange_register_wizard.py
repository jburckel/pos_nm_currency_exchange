# -*- coding: utf-8 -*-

from datetime import datetime

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosNmExchangeRegisterWizard(models.TransientModel):
    _name = 'pos.nm.exchange.register.wizard'
    _description = 'Print the Exchange Register'

    def _default_date_start(self):
        """Start of the current month in the time zone of the user."""
        tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        start = datetime.now(tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        return tz.localize(start).astimezone(pytz.utc).replace(tzinfo=None)

    date_start = fields.Datetime(string='From', required=True, default=_default_date_start,
                                 help='Operations recorded from this date and time.')
    date_stop = fields.Datetime(string='To', required=True, default=fields.Datetime.now,
                                help='Operations recorded up to this date and time.')
    config_ids = fields.Many2many(
        'pos.config', string='Points of Sale',
        help='Points of sale of the register; all of them when empty.')

    @api.constrains('date_start', 'date_stop')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_stop < wizard.date_start:
                raise ValidationError(_("The end of the period must be after its start."))

    def _nm_report_data(self):
        self.ensure_one()
        return {
            'date_start': fields.Datetime.to_string(self.date_start),
            'date_stop': fields.Datetime.to_string(self.date_stop),
            'config_ids': self.config_ids.ids,
        }

    def action_print(self):
        return self.env.ref('pos_nm_currency_exchange.action_report_exchange_register').report_action(
            [], data=self._nm_report_data())
