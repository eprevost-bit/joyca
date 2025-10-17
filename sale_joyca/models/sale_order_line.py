# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    translated_product_name = fields.Char('Nombre del producto traducido')

    # 1. Añadimos el campo para las horas de fabricación.
    # Usamos un campo Float para permitir decimales (ej: 1.5 horas).
    manufacturing_hours = fields.Float(
        string="Horas de Fabricación",
        help="Tiempo estimado de fabricación para la cantidad de esta línea."
    )

    # 2. Añadimos el campo para las horas de montaje.
    assembly_hours = fields.Float(
        string="Horas de Montaje",
        help="Tiempo estimado de montaje para la cantidad de esta línea."
    )


