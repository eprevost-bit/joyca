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
        readonly=True,
        store=True # Opcional: mejora el rendimiento si necesitas buscar o agrupar por este campo
    )
    total_amount_tax = fields.Monetary(
        string='Impuestos Totales',
        compute='_compute_sale_order_totals',
        readonly=True,
        store=True
    )
    total_amount_total = fields.Monetary(
        string='Total General',
        compute='_compute_sale_order_totals',
        readonly=True,
        store=True
    )
    # Es necesario tener un campo de moneda
    currency_id = fields.Many2one(
        'res.currency', 
        related='company_id.currency_id', 
        string='Moneda'
    )


    @api.depends('sale_order_ids.amount_untaxed', 'sale_order_ids.amount_tax', 'sale_order_ids.amount_total')
    def _compute_sale_order_totals(self):
        """
        Calcula la suma de los totales de todas las órdenes de venta
        asociadas a este proyecto.
        """
        for project in self:
            untaxed = 0.0
            tax = 0.0
            total = 0.0
            for so in project.sale_order_ids:
                untaxed += so.amount_untaxed
                tax += so.amount_tax
                total += so.amount_total
            
            project.total_amount_untaxed = untaxed
            project.total_amount_tax = tax
            project.total_amount_total = total

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
            # --- LÍNEA SIMPLIFICADA ---
            # Se ha eliminado la parte del estado del presupuesto.
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