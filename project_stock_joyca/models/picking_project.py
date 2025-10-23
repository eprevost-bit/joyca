# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class Project(models.Model):
    _inherit = "project.project"

    # --- CAMPO CALCULADO ---

    stock_move_count = fields.Integer(
        string='Materiales Utilizados',
        compute='_compute_stock_move_count'
    )

    def _compute_stock_move_count(self):
        """
        Calcula el número de movimientos de stock asociados al proyecto.
        """
        for project in self:
            project.stock_move_count = self.env['stock.move'].search_count([
                ('picking_id.project_id', '=', project.id)
            ])

    # --- PASO 1: AÑADIR LOS METADATOS DEL BOTÓN ---

    def _get_stat_buttons(self):
        """
        Hereda los botones de estadísticas del dashboard OWL
        para añadir el nuestro, usando el patrón correcto de Odoo 18.
        """
        buttons = super(Project, self)._get_stat_buttons()

        buttons.append({
            'icon': 'credit-card',
            'text': _('Materiales Utilizados'),
            'number': self.stock_move_count,
            'action_type': 'object',
            'action': 'action_view_project_stock_moves',
            'show': self.stock_move_count > 0,
            'sequence': 10,
        })

        return buttons

    # --- PASO 2: INYECTAR LA DEFINICIÓN DE LA ACCIÓN ---

    def _get_project_dashboard_data(self):

        # Obtiene todos los datos originales (incluyendo nuestros botones)
        data = super(Project, self)._get_project_dashboard_data()

        # Aseguramos que el dict 'actions' exista
        if 'actions' not in data:
            data['actions'] = {}

        # Añadimos la definición de nuestra acción
        # La clave 'stock_moves_action' DEBE COINCIDIR con el 'name'
        # del botón en _get_stat_buttons.
        action = self.env.ref('project_stock_joyca.action_project_stock_moves')
        if action:
            data['actions']['stock_moves_action'] = action.read(load=False)[0]

        return data

    def action_view_project_stock_moves(self):
        """
        Esta función abre la vista de movimientos de stock.
        """
        return {
            'name': _('Materiales Utilizados'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('picking_id.project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }