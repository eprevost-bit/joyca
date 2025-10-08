from collections import defaultdict

from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseOrderLineCustom(models.Model):
    _inherit = 'purchase.order.line'

    # 1. Campo para la casilla de selección en cada línea
    is_selected_for_email = fields.Boolean(string="Seleccionar para Correo")
    proveedor_line = fields.Many2one('res.partner', string='Proveedor', domain=[('supplier_rank', '>', 0)])


class PurchaseOrderCustom(models.Model):
    _inherit = 'purchase.order'

    def action_set_to_inicial_presupuesto(self):
        for order in self:
            # 1. Agrupar lineas por proveedor
            supplier_lines = defaultdict(lambda: self.env['purchase.order.line'])
            for line in order.order_line:
                if line.proveedor_line:
                    supplier_lines[line.proveedor_line] |= line

            if not supplier_lines:
                # Si no se asignaron proveedores, simplemente cambia el estado.
                return order.write({'state': 'inicial_presu'})

            # 2. Crear nuevos pedidos de compra
            new_orders = []
            for supplier, lines in supplier_lines.items():
                # Copiamos el pedido original
                new_order = order.copy({
                    'partner_id': supplier.id,
                    'order_line': [],  # Limpiamos las lineas para no duplicar las originales
                    'state': 'draft',  # Estado inicial para los nuevos pedidos
                })

                # Copiamos solo las lineas correspondientes a este proveedor
                for line in lines:
                    line.copy({
                        'order_id': new_order.id,
                    })
                new_orders.append(new_order.id)

            # 3. Cambiar el estado del pedido original
            order.write({'state': 'inicial_presu'})

            # Opcional: Devolver una acción para ver los nuevos pedidos creados
            return {
                'name': 'Pedidos de Compra Generados',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'list,form',
                'domain': [('id', 'in', new_orders)],
            }
        return True

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