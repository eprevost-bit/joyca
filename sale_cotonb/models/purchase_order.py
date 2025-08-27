# -*- coding: utf-8 -*-
from odoo import models, api, _, fields
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    state = fields.Selection(selection_add=[
        ('intermediate', 'Pendiente Aprobación'),
        ('purchase',),  # Esto reutiliza la definición del estado 'purchase' existente
    ], ondelete={'intermediate': 'cascade'})
    
    def action_set_to_intermediate(self):
        return self.write({'state': 'intermediate'})


    def button_confirm_intermediate(self):
        """
        Heredamos el método de confirmación de la compra.
        Después de ejecutar la lógica estándar, actualizamos el precio
        en el pedido de venta de origen.
        """
        # 1. Ejecutar la lógica original del botón.
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
                    _logger.info(
                        f"Precio actualizado para '{product.display_name}' en el pedido '{sale_order.name}'. "
                        f"Nuevo precio: {new_price:.2f}"
                    )

            # 4. NUEVA LÓGICA: Verificar si la SO de origen puede avanzar de estado.
            # Se hace aquí porque la PO ya está en estado 'purchase'.
            if sale_order.custom_state == 'waiting_purchase':
                sale_order._check_purchase_orders_status()
                
        return res