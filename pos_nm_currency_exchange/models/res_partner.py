# -*- coding: utf-8 -*-

from odoo import fields, models

ID_DOCUMENT_TYPES = [
    ('passport', 'Passport'),
    ('id_card', 'Identity Card'),
    ('driving_licence', 'Driving Licence'),
    ('residence_permit', 'Residence Permit'),
    ('other', 'Other'),
]


class ResPartner(models.Model):
    """Identity document of the customers of the exchange counter.

    Personal data: only the Point of Sale managers read and edit it, and it
    is not copied with the contact. The register reads and writes it through
    the exchange operation (with sudo), which keeps a frozen copy of it.
    """
    _inherit = 'res.partner'

    nm_id_document_type = fields.Selection(
        ID_DOCUMENT_TYPES, string='Identity Document', groups='point_of_sale.group_pos_manager', copy=False,
        help='Type of the identity document shown by the customer at the exchange counter.')
    nm_id_document_number = fields.Char(
        string='Document Number', groups='point_of_sale.group_pos_manager', copy=False)
    nm_id_document_country_id = fields.Many2one(
        'res.country', string='Issuing Country', groups='point_of_sale.group_pos_manager', copy=False)
    nm_id_document_expiry = fields.Date(
        string='Document Expiry Date', groups='point_of_sale.group_pos_manager', copy=False,
        help='The exchange counter refuses an expired document.')
    nm_nationality_id = fields.Many2one(
        'res.country', string='Nationality', groups='point_of_sale.group_pos_manager', copy=False)
    nm_birthdate = fields.Date(string='Date of Birth', groups='point_of_sale.group_pos_manager', copy=False)
