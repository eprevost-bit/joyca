# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class RenameProjectWizard(models.TransientModel):
    _name = 'rename.project.wizard'
    _description = 'Asistente para Renombrar Proyecto desde Venta'

    project_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        required=True,
        readonly=True
    )
    name_corto = fields.Char(
        string='Nombre Corto del Proyecto',
        required=True
    )

    city = fields.Selection(
        [('madrid', 'Madrid'),
         ('barcelona', 'Barcelona')],
        string='Ciudad',
        required=True
    )

    project_code_preview = fields.Char(
        string='Formato del Código',
        readonly=True,
        compute='_compute_project_code_preview'
    )

    @api.depends('city')
    def _compute_project_code_preview(self):
        for wizard in self:
            # Establecer un valor por defecto
            wizard.project_code_preview = ''
            if wizard.city:
                # Determinar el código de la secuencia
                sequence_code = 'project.code.madrid' if wizard.city == 'madrid' else 'project.code.barcelona'

                # Usamos sudo() para asegurar permisos de lectura sobre ir.sequence
                sequence = self.env['ir.sequence'].sudo().search([('code', '=', sequence_code)], limit=1)

                if sequence:
                    # Replicamos la lógica de Odoo para generar el prefijo.
                    # Esto reemplaza %(y)s con el año actual de 2 dígitos (ej: M25).
                    prefix = sequence.prefix.replace('%(y)s', fields.Date.today().strftime('%y'))

                    # Obtenemos el siguiente número y lo formateamos con el padding (ej: 0001)
                    next_number = sequence.number_next_actual
                    number_str = str(next_number).zfill(sequence.padding)

                    wizard.project_code_preview = f"{prefix}{number_str}"
                else:
                    # Si no se encuentra la secuencia, mostramos un aviso útil
                    wizard.project_code_preview = f'¡Secuencia "{sequence_code}" no encontrada!'

    def action_confirm_project_name(self):
        self.ensure_one()

        # CORRECCIÓN: Se valida con el campo correcto 'name_corto'
        if self.project_id and self.name_corto and self.city:
            sequence_code = ''
            if self.city == 'madrid':
                sequence_code = 'project.code.madrid'
            elif self.city == 'barcelona':
                sequence_code = 'project.code.barcelona'

            if not sequence_code:
                raise UserError(_('La ciudad seleccionada no tiene una secuencia de código configurada.'))

            # Esta variable SÍ contiene el código real, ej: "B250001"
            new_code = self.env['ir.sequence'].next_by_code(sequence_code)

            if not new_code:
                raise UserError(
                    _("No se pudo generar el código del proyecto. Asegúrese de que la secuencia '%s' existe y está configurada correctamente.") % sequence_code)

            # --- LA CORRECCIÓN ESTÁ AQUÍ ---
            # Ahora usamos la variable 'new_code' para componer el nombre final
            # y no el campo de previsualización.
            final_project_name = f"{new_code} - {self.name_corto}"

            self.project_id.write({
                'name': final_project_name,
                'project_code': new_code,
            })

        return {'type': 'ir.actions.act_window_close'}

