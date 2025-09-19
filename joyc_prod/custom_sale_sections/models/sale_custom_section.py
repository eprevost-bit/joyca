# models/sale_custom_section.py
from odoo import api, fields, models

class SaleCustomSection(models.Model):
    _name = 'sale.custom.section'
    _description = 'Pestaña de Sección para Presupuestos'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre de la Pestaña', required=True, default='Nueva Sección')
    sequence = fields.Integer(default=10)
    order_id = fields.Many2one('sale.order', string='Presupuesto', ondelete='cascade', required=True)
    
    currency_id = fields.Many2one(related='order_id.currency_id')
    amount_untaxed = fields.Monetary(string='Base Imponible', compute='_compute_section_total', store=True)

    @api.depends('order_id.order_line', 'order_id.order_line.price_subtotal')
    def _compute_section_total(self):
        """
        Calcula el subtotal de todas las líneas de producto que pertenecen a esta sección.
        """
        for section in self:
            # Filtramos solo las líneas que pertenecen a esta sección
            relevant_lines = section.order_id.order_line.filtered(
                lambda line: line.custom_section_id == section and line.display_type is False
            )
            section.amount_untaxed = sum(relevant_lines.mapped('price_subtotal'))