# -*- coding: utf-8 -*-

from odoo import models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'

    # --- CAMPOS ORIGINALES (Puedes mantenerlos si los necesitas en otro lugar) ---
    sale_order_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='project_id',
        string='Órdenes de Venta'
    )
    purchase_order_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='project_id',
        string='Órdenes de Compra'
    )

    unified_line_ids = fields.One2many(
        comodel_name='project.unified.line',
        inverse_name='project_id',
        string='Líneas de Venta y Compra',
        readonly=True
    )