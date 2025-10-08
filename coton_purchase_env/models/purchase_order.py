from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrderLineCustom(models.Model):
    _inherit = 'purchase.order.line'

    # 1. Campo para la casilla de selección en cada línea
    is_selected_for_email = fields.Boolean(string="Seleccionar para Correo")
    proveedor_line = fields.Many2one('res.partner', string='Proveedor')


class PurchaseOrderCustom(models.Model):
    _inherit = 'purchase.order'

    def action_send_items_by_email(self):
        self.ensure_one()

        # 2. Filtrar para obtener solo las líneas que el usuario seleccionó
        selected_lines = self.order_line.filtered(lambda line: line.is_selected_for_email)

        if not selected_lines:
            raise UserError("Por favor, seleccione al menos una partida para enviar por correo electrónico.")

        # 3. Cargar la plantilla de correo que crearemos en el siguiente paso
        template = self.env.ref('coton_purchase_env.email_template_purchase_selected_lines')

        # 4. Abrir el pop-up del correo electrónico (compositor de correo)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {
                'default_model': 'purchase.order',
                'default_res_ids': [self.id],
                'default_use_template': True,
                'default_template_id': template.id,
                'selected_line_ids': selected_lines.ids
            },
        }