# -*- coding: utf-8 -*-
from odoo import models, api, _, fields
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    x_source_sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Línea de Venta Origen',
        readonly=True,
        index=True, # Buen rendimiento para búsquedas
        copy=False  # No copiar este enlace al duplicar una OC
    )

    x_sale_invoiced_percentage = fields.Float(
        related='x_source_sale_line_id.percentage_invoiced_total',
        string='% Facturado (Venta)',
        readonly=True,
        store=True
    )



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        self.write({'state': 'purchase'})
        return res


    def run_custom_logic_before_confirm(self):

        res = self.action_set_to_intermediate()

        # 2. Iniciar nuestra lógica personalizada.
        # 2. Iniciar nuestra lógica personalizada.
        for po in self:
            # Si la compra no tiene un origen, no hacemos nada.
            if not po.origin:
                continue

            sale_order = self.env['sale.order'].search([('name', '=', po.origin)], limit=1)
            if not sale_order:
                _logger.warning(
                    f"Actualización de precios omitida: No se encontró el pedido de venta '{po.origin}' "
                    f"referenciado desde la compra '{po.name}'."
                )
                continue

            # 3. Tu lógica existente para actualizar precios en la SO.
            for line in po.order_line:
                product = line.product_id
                margin_percent = product.categ_id.margin or 0.0
                margin_decimal = margin_percent / 100.0
                sale_line_to_update = sale_order.order_line.filtered(
                    lambda sol: sol.product_id == product
                )
                if sale_line_to_update:
                    new_price = line.price_unit * (1 + margin_decimal)
                    sale_line_to_update.write({'price_unit': new_price})
                    sale_line_to_update.write({'provider_cost': line.price_unit})

                    _logger.info(
                        f"Precio actualizado para '{product.display_name}' en el pedido '{sale_order.name}'. "
                        f"Nuevo precio: {new_price:.2f}"
                    )

            # 4. NUEVA LÓGICA: Verificar si la SO de origen puede avanzar de estado.
            # Se hace aquí porque la PO ya está en estado 'purchase'.
            if sale_order.custom_state == 'waiting_purchase':
                sale_order._check_purchase_orders_status()
                
        return res