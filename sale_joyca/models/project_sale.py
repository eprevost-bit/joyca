# -*- coding: utf-8 -*-
import re
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'project.project'

    manufacturing_hours = fields.Float(
        string="Horas de Fabricación",
        help="Tiempo estimado de fabricación para la cantidad de esta línea."
    )

    # 2. Añadimos el campo para las horas de montaje.
    assembly_hours = fields.Float(
        string="Horas de Montaje",
        help="Tiempo estimado de montaje para la cantidad de esta línea."
    )




