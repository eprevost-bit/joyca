import re
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ... tu campo 'state' modificado va aquí ...
    state = fields.Selection(
        selection_add=[
            ('version', 'Versión'),
            ('sent',)
        ],
        ondelete={'version': 'cascade'}
    )

    name_presupuesto = fields.Char(string='Nombre del Presupuesto')

    def action_create_new_version(self):
        self.ensure_one()

        base_name_match = re.match(r'^(.*?)(?:-V(\d+))?$', self.name)
        base_name = base_name_match.groups()[0] if base_name_match else self.name

        related_orders = self.env['sale.order'].search([
            '|',
            ('name', '=', base_name),
            ('name', '=like', f"{base_name}-V%")
        ])

        max_version = 0
        for order in related_orders:
            version_match = re.search(r'-V(\d+)$', order.name)
            if version_match:
                max_version = max(max_version, int(version_match.group(1)))

        new_version_number = max_version + 1

        # Al copiar, reseteamos los campos que lo marcan como un pedido confirmado.
        new_quotation = self.copy(default={
            'name': f"{base_name}-V{new_version_number}",
            'origin': self.name,
            # --- CAMBIOS CLAVE AQUÍ ---
            # 1. Usamos el estado 'draft' para que se comporte como un presupuesto nuevo.
            'state': 'draft',
            # 2. Esta es la corrección principal: borramos la fecha de confirmación.
            'date_order': False,
        })

        # (Opcional pero recomendado) Cambiar el estado del presupuesto antiguo
        # para que quede claro que ha sido reemplazado por una nueva versión.
        self.write({'state': 'cancel'})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva Versión'),
            'res_model': 'sale.order',
            'res_id': new_quotation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_confirm(self):
        # Primero, ejecuta la lógica original del botón de confirmar
        res = super(SaleOrder, self).action_confirm()

        # Después, agrega tu nueva lógica para crear el proyecto
        for order in self:
            # Crea un proyecto en el modelo 'project.project'
            project = self.env['project.project'].create({
                'name': order.name,  # Nombra el proyecto como el pedido de venta
                'partner_id': order.partner_id.id, # Asigna el mismo cliente al proyecto
            })
            
            # Opcional pero recomendado: Vincula el nuevo proyecto al pedido de venta
            order.write({
                'project_id': project.id
            })
            
        return res