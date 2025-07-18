# -*- coding: utf-8 -*-
from odoo import models, fields, _, http
from odoo.exceptions import UserError

class ProjectProject(models.Model):
    _inherit = 'project.project'

    sale_order_ids = fields.One2many(
        'sale.order',
        'project_id',
        string='Órdenes de Venta'
    )

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