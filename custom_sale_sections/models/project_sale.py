# -*- coding: utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import UserError

class ProjectProject(models.Model):
    _inherit = 'project.project'

    # --- CAMPOS DE RELACIÓN Y MONEDA ---
    sale_order_ids = fields.One2many(
        'sale.order',
        'project_id',
        string='Órdenes de Venta'
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string='Moneda',
        compute='_compute_currency',
        store=True,
        readonly=True
    )
    
    # --- CAMPOS DE TOTALES GENERALES (MONETARIOS) ---
    total_amount_untaxed = fields.Monetary(
        string='Base Imponible Total',
        compute='_compute_sale_order_totals',
        store=True,
        readonly=True
    )
    total_amount_tax = fields.Monetary(
        string='Impuestos Totales',
        compute='_compute_sale_order_totals',
        store=True,
        readonly=True
    )
    total_amount_total = fields.Monetary(
        string='Total General',
        compute='_compute_sale_order_totals',
        store=True,
        readonly=True
    )
    
    # --- CAMPOS DE DESGLOSE DE PORCENTAJES (MONETARIOS) ---
    x_total_muestra = fields.Monetary(string="MUESTRA (5%)", compute='_compute_pct_totals', store=True, readonly=True)
    x_total_barniz = fields.Monetary(string="REPASO DE BARNIZ (1%)", compute='_compute_pct_totals', store=True, readonly=True)
    x_total_ofitec = fields.Monetary(string="OFICINA TÉCNICA (4%)", compute='_compute_pct_totals', store=True, readonly=True)
    x_total_repasos = fields.Monetary(string="REPASOS (1%)", compute='_compute_pct_totals', store=True, readonly=True)
    
    x_qty_cajones = fields.Float(string="TOTAL DE CAJONES", compute='_compute_service_quantities', store=True, readonly=True)
    x_qty_plataforma = fields.Float(string="IMPORTE TOTAL SUBIDA DE MATERIAL CON PLATAFORMA", compute='_compute_service_quantities', store=True, readonly=True)
    x_qty_desplazamiento = fields.Float(string="HORAS DE DESPLAZAMIENTOS", compute='_compute_service_quantities', store=True, readonly=True)
    x_qty_reparto = fields.Float(string="TOTAL HORAS REPARTO DE MATERIAL EN OBRA", compute='_compute_service_quantities', store=True, readonly=True)
    x_qty_fabricacion = fields.Float(string="TOTAL HORAS DE FABRICACIÓN", compute='_compute_service_quantities', store=True, readonly=True)
    x_qty_montaje = fields.Float(string="TOTAL HORAS DE MONTAJE", compute='_compute_service_quantities', store=True, readonly=True)

    @api.depends('company_id')
    def _compute_currency(self):
        for project in self:
            project.currency_id = project.company_id.currency_id or self.env.company.currency_id

    @api.depends('sale_order_ids.amount_untaxed', 'sale_order_ids.amount_tax', 'sale_order_ids.amount_total')
    def _compute_sale_order_totals(self):
        for project in self:
            project._calculate_and_set_totals()

    @api.depends('sale_order_ids.order_line.price_subtotal', 'sale_order_ids.order_line.product_id.default_code')
    def _compute_pct_totals(self):
        for project in self:
            project._calculate_and_set_pct_totals()

    @api.depends('sale_order_ids.order_line.product_uom_qty', 'sale_order_ids.order_line.product_id.default_code')
    def _compute_service_quantities(self):
        for project in self:
            project._calculate_and_set_service_quantities()

    @api.onchange('sale_order_ids')
    def _onchange_sale_order_ids(self):
        """
        Se dispara INMEDIATAMENTE en la interfaz para actualizar todos los campos calculados.
        """
        self._calculate_and_set_totals()
        self._calculate_and_set_pct_totals()
        self._calculate_and_set_service_quantities()

    def _calculate_and_set_totals(self):
        """Calcula los totales generales del proyecto."""
        self.total_amount_untaxed = sum(self.sale_order_ids.mapped('amount_untaxed'))
        self.total_amount_tax = sum(self.sale_order_ids.mapped('amount_tax'))
        self.total_amount_total = sum(self.sale_order_ids.mapped('amount_total'))

    def _calculate_and_set_pct_totals(self):
        """Calcula los subtotales de los servicios de porcentaje."""
        all_lines = self.sale_order_ids.mapped('order_line')
        self.x_total_muestra = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'PCT-MUESTRA').mapped('price_subtotal'))
        self.x_total_barniz = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'PCT-BARNIZ').mapped('price_subtotal'))
        self.x_total_ofitec = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'PCT-OFITEC').mapped('price_subtotal'))
        self.x_total_repasos = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'PCT-REPASOS').mapped('price_subtotal'))

    def _calculate_and_set_service_quantities(self):
        """Calcula las cantidades totales de los servicios."""
        all_lines = self.sale_order_ids.mapped('order_line')
        self.x_qty_cajones = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'SERV-CAJONES').mapped('product_uom_qty'))
        self.x_qty_plataforma = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'SERV-PLATAFORMA').mapped('product_uom_qty'))
        self.x_qty_desplazamiento = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'SERV-DESPLAZAMIENTO').mapped('product_uom_qty'))
        self.x_qty_reparto = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'SERV-REPARTO').mapped('product_uom_qty'))
        self.x_qty_fabricacion = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'SERV-FABRICACION').mapped('product_uom_qty'))
        self.x_qty_montaje = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'SERV-MONTAJE').mapped('product_uom_qty'))

    def action_send_so_list_by_email(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Este proyecto no tiene un cliente asignado para enviarle el correo."))

        presupuestos_validos = self.sale_order_ids.filtered(lambda so: so.state != 'cancel')
        if not presupuestos_validos:
            raise UserError(_("No hay presupuestos válidos (no cancelados) para enviar en este proyecto."))

        body_html = f"<p>Estimado/a {self.partner_id.name},</p>"
        body_html += "<p>A continuación, le presentamos un resumen de los presupuestos asociados a su proyecto:</p>"
        body_html += "<ul>"
        for so in presupuestos_validos:
            body_html += f"<li>{so.name}: {so.amount_total} {so.currency_id.symbol}</li>"
        body_html += "</ul>"
        body_html += "<p>Gracias por su confianza.</p>"

        compose_form_id = self.env.ref('mail.email_compose_message_wizard_form').id
        ctx = {
            'default_model': 'project.project',
            'default_res_ids': self.id,
            'default_use_template': False,
            'default_partner_ids': [self.partner_id.id],
            'default_subject': f"Resumen de Presupuestos del Proyecto: {self.name}",
            'default_body': body_html,
        }

        return {
            'name': _('Enviar Lista de Presupuestos'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }