# -*- coding: utf-8 -*-
import logging
from datetime import datetime, date, timedelta
from collections import Counter

try:
    import pytz
except ImportError:
    pytz = None

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AttendanceAutocompleteWizard(models.TransientModel):
    _name = 'attendance.autocomplete.wizard'
    _description = 'Asistente para Autocompletar Asistencias'

    # --- Campos de Configuración General ---
    operation_mode = fields.Selection([
        ('fill_range', 'Autocompletar Rango de Fechas'),
        ('copy_week', 'Copiar Patrón Semanal')
    ], string="Operación a Realizar", default='fill_range', required=True)

    employee_ids = fields.Many2many('hr.employee', string="Empleados",
                                    help="Dejar en blanco para aplicar a todos los empleados activos.")

    # --- Campos para 'Autocompletar Rango de Fechas' ---
    start_date = fields.Date(string="Fecha de Inicio", default='2025-09-25')
    end_date = fields.Date(string="Fecha de Fin", default='2025-11-01')
    check_in_time = fields.Float(string="Hora de Entrada", default=9.0, help="Ejemplo: 9.5 para 09:30")
    check_out_time = fields.Float(string="Hora de Salida", default=17.0,
                                  help="Ejemplo: 17.0 para 17:00. Debe ser mayor a la hora de entrada.")

    # --- Campos para 'Copiar Patrón Semanal' ---
    source_date = fields.Date(string="Fecha de la Semana de Origen", default='2025-09-15',
                              help="Seleccione cualquier día de la semana que desea copiar.")
    target_date = fields.Date(string="Fecha de la Semana de Destino", default='2025-09-22',
                              help="Seleccione cualquier día de la semana que desea rellenar.")
    fill_missing_days = fields.Boolean(string="Completar días faltantes", default=True,
                                       help="Si está marcado, después de copiar el patrón, rellenará los días laborables que queden vacíos con el horario más común de la semana de origen.")

    @api.constrains('check_in_time', 'check_out_time')
    def _check_times(self):
        if self.operation_mode == 'fill_range' and self.check_in_time >= self.check_out_time:
            raise UserError(_("La hora de salida debe ser posterior a la hora de entrada."))

    def _get_employees(self):
        if self.employee_ids:
            return self.employee_ids
        return self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])

    def _dt_to_utc(self, dt_naive):
        if not pytz:
            raise UserError(_("La librería 'pytz' no está instalada."))
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        dt_aware = user_tz.localize(dt_naive)
        return dt_aware.astimezone(pytz.utc).replace(tzinfo=None)

    def _float_to_datetime(self, target_date, float_time):
        hours = int(float_time)
        minutes = int((float_time * 60) % 60)
        return datetime.combine(target_date, datetime.min.time()).replace(hour=hours, minute=minutes)

    def action_execute_autocomplete(self):
        self.ensure_one()
        if self.operation_mode == 'fill_range':
            return self.execute_fill_range()
        elif self.operation_mode == 'copy_week':
            return self.execute_copy_week()

    def execute_fill_range(self):
        employees = self._get_employees()
        if not employees:
            raise UserError(_("No se encontraron empleados para procesar."))

        current_date = self.start_date
        attendances_to_create = []

        while current_date <= self.end_date:
            if current_date.weekday() != 6:  # Excluir Domingos
                check_in_naive = self._float_to_datetime(current_date, self.check_in_time)
                check_out_naive = self._float_to_datetime(current_date, self.check_out_time)
                check_in_utc = self._dt_to_utc(check_in_naive)
                check_out_utc = self._dt_to_utc(check_out_naive)

                for emp in employees:
                    domain = [
                        ('employee_id', '=', emp.id),
                        ('check_in', '>=', datetime.combine(current_date, datetime.min.time())),
                        ('check_in', '<=', datetime.combine(current_date, datetime.max.time())),
                    ]
                    if not self.env['hr.attendance'].search_count(domain):
                        attendances_to_create.append({
                            'employee_id': emp.id,
                            'check_in': check_in_utc,
                            'check_out': check_out_utc,
                        })
            current_date += timedelta(days=1)

        if attendances_to_create:
            self.env['hr.attendance'].create(attendances_to_create)

        return self._show_message(
            _("Proceso completado. Se han creado %d nuevos registros de asistencia.") % len(attendances_to_create))

    def execute_copy_week(self):
        source_start_week = self.source_date - timedelta(days=self.source_date.weekday())
        target_start_week = self.target_date - timedelta(days=self.target_date.weekday())
        employees = self._get_employees()

        source_end_week_dt = datetime.combine(source_start_week + timedelta(days=6), datetime.max.time())
        source_attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', employees.ids),
            ('check_in', '>=', source_start_week),
            ('check_in', '<=', source_end_week_dt)
        ])

        # --- Parte 1: Copiar patrón exacto ---
        attendances_to_create = []
        copied_attendances_map = {emp.id: set() for emp in employees}
        for att in source_attendances:
            days_diff = att.check_in.date() - source_start_week
            target_date = target_start_week + days_diff

            # Asegurarse que el día de la semana no sea domingo en la semana de destino
            if target_date.weekday() == 6:
                continue

            target_check_in = datetime.combine(target_date, att.check_in.time())
            target_check_out = datetime.combine(target_date, att.check_out.time())

            domain = [
                ('employee_id', '=', att.employee_id.id),
                ('check_in', '>=', target_check_in.replace(hour=0, minute=0)),
                ('check_in', '<=', target_check_in.replace(hour=23, minute=59)),
            ]
            if not self.env['hr.attendance'].search_count(domain):
                attendances_to_create.append({
                    'employee_id': att.employee_id.id,
                    'check_in': target_check_in,
                    'check_out': target_check_out,
                })
            copied_attendances_map[att.employee_id.id].add(target_date.weekday())

        if attendances_to_create:
            self.env['hr.attendance'].create(attendances_to_create)

        # --- Parte 2: Rellenar días faltantes con horario "inteligente" ---
        attendances_to_fill = []
        if self.fill_missing_days and source_attendances:
            # Calcular el horario más común de la semana de origen
            check_in_times = [att.check_in.time() for att in source_attendances]
            check_out_times = [att.check_out.time() for att in source_attendances]
            most_common_in = Counter(check_in_times).most_common(1)[0][0]
            most_common_out = Counter(check_out_times).most_common(1)[0][0]

            for i in range(6):  # Lunes a Sábado
                current_target_date = target_start_week + timedelta(days=i)
                for emp in employees:
                    # Comprobar si el empleado ya tiene un registro en este día
                    domain = [
                        ('employee_id', '=', emp.id),
                        ('check_in', '>=', datetime.combine(current_target_date, datetime.min.time())),
                        ('check_in', '<=', datetime.combine(current_target_date, datetime.max.time())),
                    ]
                    if not self.env['hr.attendance'].search_count(domain):
                        # Si no tiene registro, crearlo con el horario común
                        check_in_utc = self._dt_to_utc(datetime.combine(current_target_date, most_common_in))
                        check_out_utc = self._dt_to_utc(datetime.combine(current_target_date, most_common_out))
                        attendances_to_fill.append({
                            'employee_id': emp.id,
                            'check_in': check_in_utc,
                            'check_out': check_out_utc,
                        })

            if attendances_to_fill:
                self.env['hr.attendance'].create(attendances_to_fill)

        message = _("Proceso de copia completado. Se crearon %d registros por copia y %d por relleno.") % (
            len(attendances_to_create), len(attendances_to_fill))
        return self._show_message(message)

    def _show_message(self, message, title=None):
        if title is None:
            title = _('Proceso Finalizado')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': True,
            }
        }