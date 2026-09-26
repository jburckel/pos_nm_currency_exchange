from odoo import api, models


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _get_xml_ids_to_load(self):
        # The receipt templates rendered in the register are loaded by key:
        # add the exchange receipt to the core list.
        return super()._get_xml_ids_to_load() + ['pos_nm_currency_exchange.pos_exchange_receipt']
