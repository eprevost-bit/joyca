# -*- coding: utf-8 -*-
import re
from odoo import models, fields, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo 'state' que ya teníamos
    state = fields.Selection(
        selection_add=[
            ('version', 'Versión'),
            ('sent',)
        ], 
        ondelete={'version': 'cascade'}
    )

    def action_create_new_version(self):
        self.ensure_one()  # Aseguramos que solo se ejecuta para un registro

        # Usamos expresiones regulares para encontrar el nombre base y la versión
        match = re.match(r'^(.*?)(?:-V(\d+))?$', self.name)
        base_name, version_number_str = match.groups()
        current_version = int(version_number_str) if version_number_str else 0

        new_version_number = 0

        # --- Lógica para manejar el presupuesto ORIGINAL ---
        if current_version == 0:
            # Si es el presupuesto base (ej. S00040), lo renombramos a V1
            # y lo ponemos en estado 'Versión'.
            self.write({
                'name': f"{base_name}-V1",
                'state': 'version'
            })
            # La nueva versión que vamos a crear será la V2
            new_version_number = 2
        else:
            # Si ya es una versión (ej. S00040-V1), solo cambiamos su estado a 'Versión'.
            self.write({
                'state': 'version'
            })
            # La nueva versión será la siguiente a la actual
            new_version_number = current_version + 1

        self.flush_model(['name', 'state'])
        new_version_name = f"{base_name}-V{new_version_number}"
        new_quotation = self.copy(default={
            'name': new_version_name,
            'state': 'draft',  # El nuevo presupuesto empieza como un borrador activo.
            'origin': self.name,  # Guardamos como origen el nombre del presupuesto del que venimos
        })

        # Devolvemos una acción para que Odoo abra el nuevo presupuesto en pantalla
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Version'),
            'res_model': 'sale.order',
            'res_id': new_quotation.id,
            'view_mode': 'form',
            'target': 'current',
        }