from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()

        # Buscar el primer producto fabricable en el presupuesto
        product_to_produce = self.order_line.filtered(
            lambda line: line.product_id.type == 'product' and line.product_id.bom_ids
        )[:1].product_id

        if not product_to_produce:
            raise UserError("No hay un producto fabricable con BoM en el presupuesto.")

        # Crear Orden de Fabricación
        mo = self.env['mrp.production'].create({
            'product_id': product_to_produce.id,
            'product_qty': 1,  # Ajusta según la cantidad
            'bom_id': product_to_produce.bom_ids[:1].id,
            'origin': self.name,  # Referencia al presupuesto
        })
        return res