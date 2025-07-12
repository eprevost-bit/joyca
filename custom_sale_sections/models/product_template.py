# custom_sale_sections/models/product_template.py
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_section_percentage = fields.Float(
        string="Porcentaje para Sección (%)",
        help="Introduce el valor en decimal. Por ejemplo, para un 15%, escribe 0.15. Este campo se usa para calcular costes en secciones de venta personalizadas."
    )