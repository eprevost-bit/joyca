# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class RenameProjectWizard(models.TransientModel):
    _name = 'rename.project.wizard'
    _description = 'Asistente para Renombrar Proyecto desde Venta'

    # Campo para guardar el ID del proyecto que vamos a renombrar
    project_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        required=True,
        readonly=True
    )
    # Campo para que el usuario escriba el nuevo nombre
    name = fields.Char(
        string='Nombre del Proyecto',
        required=True
    )

    # Esta función se ejecuta al pulsar el botón "Confirmar"
    def action_confirm_project_name(self):
        self.ensure_one()
        if self.project_id and self.name:
            # Escribimos el nuevo nombre en el proyecto original
            self.project_id.write({'name': self.name})
        return {'type': 'ir.actions.act_window_close'}