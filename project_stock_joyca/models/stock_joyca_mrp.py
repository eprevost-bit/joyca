from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    # Campo helper para poder usar el widget 'monetary' en la vista
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )

    # 1. Coste unitario (CORREGIDO)
    x_coste_unitario = fields.Float(
        string='Coste unitario',
        compute='_compute_coste_unitario', # Cambiado de 'related' a 'compute'
        digits='Product Price',
        store=True, # Lo mantenemos para que se almacene
        readonly=True, # Sigue siendo de solo lectura
    )

    # 2. Coste total (Optimizado)
    x_coste_total = fields.Float(
        string='Coste total',
        compute='_compute_coste_total',
        digits='Product Price',
        store=True,
    )

    @api.depends('product_id') # Ahora solo depende del producto
    def _compute_coste_unitario(self):
        """
        Calcula el coste unitario leyendo el 'standard_price' del producto.
        """
        for move in self:
            move.x_coste_unitario = move.product_id.standard_price

    @api.depends('product_uom_qty', 'x_coste_unitario') # Optimizado para depender del campo de arriba
    def _compute_coste_total(self):
        """
        Calcula el coste total multiplicando la cantidad
        por el coste unitario ya calculado.
        """
        for move in self:
            move.x_coste_total = move.product_uom_qty * move.x_coste_unitario