# -*- coding: utf-8 -*-
from odoo import models, fields

class DownpaymentConcept(models.Model):
    _name = 'downpayment.concept'
    _description = 'Concepto de Anticipo para Facturas'
    _order = 'sequence, id'

    name = fields.Char(
        string='Nombre del Concepto',
        required=True,
        translate=True
    )
    invoice_description = fields.Text(
        string='Descripción en Factura',
        required=True,
        help="Texto que aparecerá en la línea de la factura. Puedes usar placeholders como: {order_name} y {order_date}."
    )
    sequence = fields.Integer(string='Secuencia', default=10)