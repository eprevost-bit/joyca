# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Campo 'color' que la vista Gantt utilizará.
    # Será un campo calculado que depende de tu campo 'overtime_status'.
    color = fields.Integer(string='Color Index', compute='_compute_color', store=True) # store=True para indexación/filtrado si es necesario

    @api.depends('overtime_status') # Ahora depende de 'overtime_status'
    def _compute_color(self):
        """
        Calcula el índice de color basado en el estado 'overtime_status'.
        - Verde (10) para 'approved'
        - Rojo (2) para 'refused'
        - Gris (por defecto, 0 o cualquier otro) para 'to_approve' (Pendiente)
        """
        for attendance in self:
            if attendance.overtime_status == 'approved':
                attendance.color = 10  # El color verde en la paleta de Odoo
            elif attendance.overtime_status == 'refused':
                attendance.color = 2   # El color rojo en la paleta de Odoo
            else:
                attendance.color = 0   # Color por defecto (gris/azul claro) para 'to_approve'