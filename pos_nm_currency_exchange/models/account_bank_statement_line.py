# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_exchange_leg(self):
        """The two lines of an exchange operation (and of its reversal) go
        together: deleting one of them, for instance from the cash moves of
        the register, would leave the drawers and the commission account
        off by one leg while the operation still reports its commission."""
        exchanges = self.env['pos.nm.exchange'].sudo().search([
            '|', '|', '|',
            ('statement_line_in_id', 'in', self.ids),
            ('statement_line_out_id', 'in', self.ids),
            ('statement_line_cancel_in_id', 'in', self.ids),
            ('statement_line_cancel_out_id', 'in', self.ids),
        ], limit=1)
        if exchanges:
            raise UserError(_(
                "This cash move belongs to the currency exchange operation %s and cannot be deleted. "
                "A Point of Sale manager can cancel the operation instead.", exchanges.name))
