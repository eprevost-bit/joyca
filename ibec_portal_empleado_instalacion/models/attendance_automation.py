from odoo import models, fields, api
from datetime import datetime, timedelta, time
import random
import logging

_logger = logging.getLogger(__name__)


class AttendanceAutomation(models.Model):
    _name = 'attendance.automation'
    _description = 'Automatización de Registros Horarios'

    @api.model
    def process_weekly_attendance(self):
        _logger.info("⏰ Ejecutando cron de asistencia semanal")

        today = fields.Date.today()
        last_sunday = today - timedelta(days=today.weekday() + 1)
        week_start = last_sunday - timedelta(days=6)

        employees = self.env['hr.employee'].search([('active', '=', True)])

        for employee in employees:
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', week_start),
                ('check_in', '<=', last_sunday)
            ])

            for att in attendances:
                att.write({'active': False})

            days = {att.check_in.date() for att in attendances if att.check_in}

            for day in days:
                morning_in = datetime.combine(day, time(8, random.randint(55, 59)))
                morning_out = datetime.combine(day, time(12, random.randint(55, 59)))

                afternoon_in = datetime.combine(day, time(14, random.randint(55, 59)))
                afternoon_out = datetime.combine(day, time(17, random.randint(55, 59)))

                self.env['hr.attendance'].create({
                    'employee_id': employee.id,
                    'check_in': morning_in,
                    'check_out': morning_out,
                })

                self.env['hr.attendance'].create({
                    'employee_id': employee.id,
                    'check_in': afternoon_in,
                    'check_out': afternoon_out,
                })
