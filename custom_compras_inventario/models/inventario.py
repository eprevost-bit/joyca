from odoo import models, fields, api


class MovimientoStock(models.Model):
    _inherit = "stock.move"

    proyecto_id = fields.Many2one(
        "project.project",
        string="Proyecto",
        domain="[('active', '=', True)]"
    )

    @api.model_create_multi
    def create(self, vals_list):
        PurchaseLine = self.env["purchase.order.line"]

        for vals in vals_list:
            purchase_line_id = vals.get("purchase_line_id")
            if purchase_line_id and not vals.get("proyecto_id"):
                purchase_line = PurchaseLine.browse(purchase_line_id)
                if purchase_line.exists() and purchase_line.proyecto_id:
                    vals["proyecto_id"] = purchase_line.proyecto_id.id

        return super().create(vals_list)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    proyecto_id = fields.Many2one(
        related="move_id.proyecto_id",
        comodel_name="project.project",
        string="Proyecto",
        store=True,
        readonly=True
    )
