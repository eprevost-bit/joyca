# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_create(self, name):
        # AQUÍ ESTÁ EL CONTROL:
        # Le preguntamos al "identificador de llamadas" (el contexto) si la llamada
        # viene de un lugar relacionado con ventas.
        if self.env.context.get('sale_ok') or self.env.context.get('active_model') == 'sale.order':
            # Como la respuesta es SÍ, tomamos el control y creamos el producto
            # con nuestras propias reglas (tipo servicio, sale_ok=True, etc.).
            vals = {
                'name': name,
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                'invoice_policy': 'order',
            }
            product = self.create(vals)
            return product.id, product.display_name

        # Si la respuesta es NO (ej. la llamada viene de una orden de compra),
        # no hacemos nada especial y dejamos que Odoo actúe de forma estándar.
        return super(ProductProduct, self).name_create(name)