# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    margin = fields.Float(
        string="Margen (%)",
        help="Define el margen de beneficio para esta categoría. "
             "Por ejemplo, para un 25%, introduce 25."
    )