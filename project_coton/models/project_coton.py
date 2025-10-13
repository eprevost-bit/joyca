# -*- coding: utf-8 -*-

from odoo import models, fields

class ProjectProject(models.Model):
    """
    Hereda del modelo project.project para agregar la relación
    con las órdenes de venta y compra.
    """
    _inherit = 'project.project'

    # Campo One2many para las órdenes de venta (presupuestos)
    # El 'inverse_name' es el campo Many2one en el modelo 'sale.order'
    sale_order_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='project_id',
        string='Órdenes de Venta'
    )

    # Campo One2many para las órdenes de compra
    # El 'inverse_name' es el campo Many2one en el modelo 'purchase.order'
    purchase_order_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='project_id',
        string='Órdenes de Compra'
    )