# -*- coding: utf-8 -*-
from odoo import models, fields, _, http, api
from odoo.exceptions import UserError

class ProjectProject(models.Model):
    _inherit = 'project.project'

    sale_order_ids = fields.One2many(
        'sale.order',
        'project_id',
        string='Órdenes de Venta'
    )
    
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
    currency_id = fields.Many2one(
        'res.currency', 
        related='company_id.currency_id', 
        string='Moneda'
    )
    
    x_total_muestra = fields.Monetary(string="Total Muestras (5%)", compute='_compute_pct_totals', store=True, readonly=True)
    x_total_barniz = fields.Monetary(string="Total Barniz (1%)", compute='_compute_pct_totals', store=True, readonly=True)
    x_total_ofitec = fields.Monetary(string="Total Oficina Téc. (4%)", compute='_compute_pct_totals', store=True, readonly=True)
    x_total_repasos = fields.Monetary(string="Total Repasos (1%)", compute='_compute_pct_totals', store=True, readonly=True)

    
    def _calculate_and_set_pct_totals(self):
        all_lines = self.sale_order_ids.mapped('order_line')
        self.x_total_muestra = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'PCT-MUESTRA').mapped('price_subtotal'))
        self.x_total_barniz = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'PCT-BARNIZ').mapped('price_subtotal'))
        self.x_total_ofitec = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'PCT-OFITEC').mapped('price_subtotal'))
        self.x_total_repasos = sum(all_lines.filtered(lambda l: l.product_id.default_code == 'PCT-REPASOS').mapped('price_subtotal'))
        
        
    # --- MÉTODO DE CÁLCULO CENTRALIZADO ---
    def _calculate_and_set_totals(self):
        """
        Lógica de cálculo reutilizable.
        Funciona tanto para el onchange como para el compute.
        """
        untaxed = sum(self.sale_order_ids.mapped('amount_untaxed'))
        tax = sum(self.sale_order_ids.mapped('amount_tax'))
        total = sum(self.sale_order_ids.mapped('amount_total'))
        self.total_amount_untaxed = untaxed
        self.total_amount_tax = tax
        self.total_amount_total = total
        
    @api.depends('sale_order_ids.order_line.price_subtotal', 'sale_order_ids.order_line.product_id.default_code')
    def _compute_pct_totals(self):
        for project in self:
            project._calculate_and_set_pct_totals()

    # --- ONCHANGE para la Interfaz de Usuario (UI) ---
    @api.onchange('sale_order_ids')
    def _onchange_sale_order_ids(self):
        """
        Se dispara INMEDIATAMENTE en la interfaz cuando añades,
        editas o eliminas una línea de presupuesto.
        """
        # Usamos la lógica centralizada
        self._calculate_and_set_totals()

    # --- COMPUTE para la Base de Datos (Server) ---
    @api.depends('sale_order_ids.amount_untaxed', 'sale_order_ids.amount_tax', 'sale_order_ids.amount_total')
    def _compute_sale_order_totals(self):
        """
        Se dispara al guardar o cuando hay cambios a nivel de servidor.
        Esencial para la integridad de los datos.
        """
        for project in self:
            # Usamos la lógica centralizada
            project._calculate_and_set_totals()
            
    # Tu método para enviar el correo (sin cambios)
    def action_send_so_list_by_email(self):
        # ... (el resto de tu código para el botón de email) ...
        # (El código que proporcionaste para este método es correcto y no necesita cambios)
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