from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    archived = fields.Boolean(string="Archivado", default=False)
    auto_generated = fields.Boolean(string="Generado Automáticamente", default=False)

    x_worked_time_calculated = fields.Float(
        string="Tiempo Calculado",
        compute='_compute_worked_time_calculated',
        store=True,
        help="Calcula las horas trabajadas directamente de la entrada y salida."
    )

    @api.depends('check_in', 'check_out')
    def _compute_worked_time_calculated(self):
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                delta = attendance.check_out - attendance.check_in
                attendance.x_worked_time_calculated = delta.total_seconds() / 3600.0
            else:
                attendance.x_worked_time_calculated = 0.0

    @api.depends('x_worked_time_calculated')
    def _compute_worked_hours(self):
        for attendance in self:
            attendance.worked_hours = attendance.x_worked_time_calculated

    # Validación
    @api.constrains('employee_id', 'check_in', 'check_out')
    def _check_attendance_overlap(self):
        for att in self:
            if not att.check_in:
                continue

            check_out = att.check_out or att.check_in

            domain = [
                ('id', '!=', att.id),
                ('employee_id', '=', att.employee_id.id),
                ('check_in', '<', check_out),
                ('check_out', '>', att.check_in),
            ]

            if self.search_count(domain):
                raise ValidationError(_(
                    "Este registro se solapa con otro fichaje existente."
                ))
