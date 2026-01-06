from odoo import models, fields

class LineaOrdenCompra(models.Model):
    _inherit = "purchase.order.line"

    proyecto_id = fields.Many2one(
        comodel_name="project.project",
        string="Proyecto",
        domain="[('active', '=', True)]"
    )
