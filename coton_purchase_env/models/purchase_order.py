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

    # Redefinimos el campo 'state' para eliminar los estados 'sent' e 'intermediate'
    # y mantener el estado personalizado 'inicial_presu'.
    # Los estados base de Odoo son: draft, sent, to approve, purchase, done, cancel.
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to approve', 'A Aprobar'),
        ('inicial_presu', 'Presupuesto Inicial'),
        ('purchase', 'Orden de Compra'),
        ('done', 'Bloqueado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', readonly=True, index=True, copy=False, default='draft', tracking=True)

    number = fields.Float(string="numero de acciones")

    def action_set_to_inicial_presupuesto(self):
        all_new_orders = []
        for order in self:
            origin_name = order.origin
            # 1. Agrupar lineas por proveedor
            supplier_lines = defaultdict(lambda: self.env['purchase.order.line'])
            for line in order.order_line:
                if line.proveedor_line:
                    supplier_lines[line.proveedor_line] |= line

            if not supplier_lines:
                # Si no se asignaron proveedores, simplemente cambia el estado y continúa.
                order.write({'state': 'inicial_presu'})
                continue

            # 2. Crear nuevos pedidos de compra
            new_orders_for_current = []
            for supplier, lines in supplier_lines.items():
                # Copiamos el pedido original
                new_order = order.copy({
                    'partner_id': supplier.id,
                    'order_line': [],  # Limpiamos las lineas para no duplicar las originales
                    'state': 'draft',  # Estado inicial para los nuevos pedidos
                })
                new_order.write({'origin': origin_name, 'number': 1})
                # Copiamos solo las lineas correspondientes a este proveedor
                for line in lines:
                    line.copy({
                        'order_id': new_order.id,
                        'x_source_sale_line_id': line.x_source_sale_line_id.id
                    })

                new_orders_for_current.append(new_order.id)

            # 3. Cambiar el estado del pedido original
            if new_orders_for_current:
                order.write({'state': 'inicial_presu'})
                all_new_orders.extend(new_orders_for_current)

        # 4. Opcional: Devolver una acción para ver todos los nuevos pedidos creados
        if all_new_orders:
            tree_view_id = self.env.ref('purchase.purchase_order_tree').id
            form_view_id = self.env.ref('purchase.purchase_order_form').id
            return {
                'name': 'Pedidos de Compra Generados',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'tree,form',
                'views': [(tree_view_id, 'list'), (form_view_id, 'form')],
                'domain': [('id', 'in', all_new_orders)],
                'target': 'current',  # Abre en la misma pestaña
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