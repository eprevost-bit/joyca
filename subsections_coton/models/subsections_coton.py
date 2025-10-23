# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SubsectionsCoton(models.Model):
    _name = 'subsections.coton'
    _description = 'Subsections for Sale Order Lines'

    name = fields.Char(string='Name')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', ondelete='cascade')

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for subsection in self:
            subsection.subtotal = subsection.quantity * subsection.price_unit


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # --- ¡CAMBIO 1: QUITAR 'display_type' Y USAR UN BOOLEANO! ---
    is_subsection_line = fields.Boolean(
        string="Is Subsection Line",
        default=False,
        copy=False  # No queremos copiar esto al duplicar
    )

    subsection_ids = fields.One2many('subsections.coton', 'order_line_id', string='Subsections')
    total_subsections = fields.Float(string='Total Subsections', compute='_compute_total_subsections', store=True)

    @api.depends('subsection_ids.subtotal')
    def _compute_total_subsections(self):
        for line in self:
            line.total_subsections = sum(sub.subtotal for sub in line.subsection_ids)

    # --- ¡CAMBIO 2: MODIFICAR EL ONCHANGE! ---
    @api.onchange('subsection_ids', 'is_subsection_line')
    def _onchange_subsections(self):
        """
        Actualiza la línea principal SI es una línea de subsección.
        """
        # Esta comprobación es VITAL.
        if self.is_subsection_line:
            self.price_unit = sum(sub.subtotal for sub in self.subsection_ids)
            self.product_uom_qty = 1

            # --- ¡CAMBIO 3: ASIGNAR EL PRODUCTO CONTENEDOR! ---
            if not self.product_id:
                # Asegúrate de que el XML ID coincide (mi_modulo.product_subsection_container)
                prod = self.env.ref('subsections_coton.product_subsection_container', raise_if_not_found=False)
                if prod:
                    self.product_id = prod.id
                else:
                    # Si no encuentra el producto, es mejor avisar.
                    raise UserError(
                        _("No se encuentra el producto 'Contenedor de Subsección'. Contacte al administrador."))

    # --- ¡CAMBIO 4: ASEGURAR EL PRODUCTO AL CREAR! ---
    # Esto hace el XML del botón 'Add Subsection' más robusto.
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_subsection_line') and not vals.get('product_id'):
                prod = self.env.ref('subsections_coton.product_subsection_container', raise_if_not_found=False)
                if prod:
                    vals['product_id'] = prod.id
                    vals['product_uom_qty'] = 1  # Forzamos la cantidad
                    # El precio se calculará con el onchange al añadir subsecciones
        return super().create(vals_list)