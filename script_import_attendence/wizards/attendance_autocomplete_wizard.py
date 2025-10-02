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
    start_date = fields.Date(string="Fecha de Inicio", required=True, default=fields.Date.today)
    end_date = fields.Date(string="Fecha de Fin", required=True, default=fields.Date.today)
    check_in_time = fields.Float(string="Hora de Entrada", default=9.0)
    check_out_time = fields.Float(string="Hora de Salida", default=17.0)

    # --- Campos para 'Copiar Patrón Semanal' ---
    source_week_date = fields.Date(string="Día de la Semana de Origen", default=fields.Date.today)
    target_week_date = fields.Date(string="Día de la Semana de Destino", default=fields.Date.today)
    fill_missing_days = fields.Boolean(string="Completar días faltantes", default=True)

    @api.constrains('start_date', 'end_date')
    def _check_fill_dates(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise UserError(_("La fecha de fin no puede ser anterior a la de inicio."))

    def _get_employees(self):
        return self.employee_ids or self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])

    def _dt_to_utc(self, dt_naive):
        if not pytz: raise UserError(_("La librería 'pytz' no está instalada."))
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        return user_tz.localize(dt_naive).astimezone(pytz.utc).replace(tzinfo=None)

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
        _logger.info("--- INICIANDO AUTOCOMPLETAR RANGO ---")
        _logger.info(f"Rango seleccionado: Desde {self.start_date} hasta {self.end_date}")

        employees = self._get_employees()
        current_date = self.start_date
        attendances_to_create = []

        # Bucle que respeta estrictamente las fechas de inicio y fin
        while current_date <= self.end_date:
            _logger.info(f"Procesando día: {current_date}")
            if current_date.weekday() != 6:  # Excluir Domingos (Lunes=0, Domingo=6)
                check_in_utc = self._dt_to_utc(self._float_to_datetime(current_date, self.check_in_time))
                check_out_utc = self._dt_to_utc(self._float_to_datetime(current_date, self.check_out_time))
                for emp in employees:
                    domain = [
                        ('employee_id', '=', emp.id),
                        ('check_in', '>=', datetime.combine(current_date, datetime.min.time())),
                        ('check_in', '<=', datetime.combine(current_date, datetime.max.time()))
                    ]
                    if not self.env['hr.attendance'].search_count(domain):
                        attendances_to_create.append(
                            {'employee_id': emp.id, 'check_in': check_in_utc, 'check_out': check_out_utc})
            current_date += timedelta(days=1)

        if attendances_to_create:
            self.env['hr.attendance'].create(attendances_to_create)

        _logger.info(f"--- FIN. Se crearon {len(attendances_to_create)} registros. ---")
        return self._show_message(_("Proceso completado. Se crearon %d registros.") % len(attendances_to_create))

    def execute_copy_week(self):
        # Esta función sigue funcionando como antes, para copiar semanas completas
        source_start = self.source_week_date - timedelta(days=self.source_week_date.weekday())
        target_start = self.target_week_date - timedelta(days=self.target_week_date.weekday())
        employees = self._get_employees()
        source_atts = self.env['hr.attendance'].search(
            [('employee_id', 'in', employees.ids), ('check_in', '>=', source_start),
             ('check_in', '<', source_start + timedelta(days=7))])

        atts_to_create = []
        for att in source_atts:
            days_diff = att.check_in.date() - source_start
            target_date = target_start + days_diff
            if target_date.weekday() == 6: continue
            target_check_in = datetime.combine(target_date, att.check_in.time())
            target_check_out = datetime.combine(target_date, att.check_out.time())
            domain = [('employee_id', '=', att.employee_id.id),
                      ('check_in', '>=', target_check_in.replace(hour=0, minute=0)),
                      ('check_in', '<=', target_check_in.replace(hour=23, minute=59))]
            if not self.env['hr.attendance'].search_count(domain):
                atts_to_create.append(
                    {'employee_id': att.employee_id.id, 'check_in': target_check_in, 'check_out': target_check_out})

        if atts_to_create: self.env['hr.attendance'].create(atts_to_create)
        # Aquí se podría añadir la lógica de relleno inteligente si se desea
        return self._show_message(_("Copia semanal completada. Se crearon %d registros.") % len(atts_to_create))

    def _show_message(self, message, title=None):
        if title is None: title = _('Proceso Finalizado')
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': title, 'message': message, 'sticky': True}}