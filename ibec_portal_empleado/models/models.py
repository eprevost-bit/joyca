from odoo import models, fields, api


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    archived = fields.Boolean(string="Archivado", default=False)
    auto_generated = fields.Boolean(string="Generado Automáticamente", default=False)

    x_worked_time_calculated = fields.Float(
        string="Tiempo Calculado",
        compute='_compute_worked_time_calculated',
        store=True,  # Opcional: para poder buscar y agrupar por este campo
        help="Calcula las horas trabajadas directamente de la entrada y salida, sin otras consideraciones."
    )

    @api.depends('check_in', 'check_out')
    def _compute_worked_time_calculated(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in:
                delta = attendance.check_out - attendance.check_in
                attendance.x_worked_time_calculated = delta.total_seconds() / 3600.0
            else:
                attendance.x_worked_time_calculated = 0.0

    # 2. Hacemos que el cálculo de 'worked_hours' dependa de tu campo
    @api.depends('x_worked_time_calculated')
    def _compute_worked_hours(self):
        for attendance in self:
            attendance.worked_hours = attendance.x_worked_time_calculated