# -*- coding: utf-8 -*-
import base64
import logging
import io  # <-- CORRECCIÓN: Librería añadida
import re
from datetime import datetime

# Es importante tener pytz para el manejo de zonas horarias
try:
    import pytz
except ImportError:
    pytz = None

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    _logger.warning("La librería openpyxl no está instalada. (pip install openpyxl).")
    openpyxl = None


class AttendanceImportWizard(models.TransientModel):
    _name = 'attendance.import.wizard'
    _description = 'Wizard para Importar Asistencias desde Excel'

    excel_file = fields.Binary(string="Archivo Excel (.xlsx)", required=True)
    excel_filename = fields.Char(string="Nombre del Archivo")

    overwrite_existing = fields.Boolean(
        string="Sobrescribir asistencias existentes",
        default=False,
        help="Si está marcado, las asistencias existentes para el mismo empleado y día serán eliminadas."
    )

    def action_import_attendance(self):
        if not openpyxl:
            raise UserError(_("La librería 'openpyxl' no está instalada."))

        if not self.excel_file:
            raise UserError(_("Por favor, suba un archivo Excel para importar."))

        try:
            file_content = base64.b64decode(self.excel_file)
            workbook = openpyxl.load_workbook(filename=io.BytesIO(file_content))
            sheet = workbook.active
        except Exception as e:
            raise UserError(
                _("No se pudo leer el archivo. Asegúrese de que es un archivo .xlsx válido. Error: %s") % str(e))

        header = [str(cell.value).lower().strip() if cell.value else '' for cell in sheet[1]]

        # Validar que las columnas necesarias existan
        required_cols = ['empleado', 'entrada', 'salida']
        if not all(col in header for col in required_cols):
            raise UserError(
                _("El archivo Excel debe contener las siguientes columnas en la primera fila: %s") % ", ".join(
                    required_cols))

        header_indices = {name: index for index, name in enumerate(header)}

        attendances_to_create = []
        errors = []
        employee_cache = {}  # Caché para no buscar el mismo empleado una y otra vez

        for row_index, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            values = {col: row[idx].value for col, idx in header_indices.items()}

            employee_name_raw = values.get('empleado')
            check_in_val = values.get('entrada')
            check_out_val = values.get('salida')

            if not employee_name_raw or not check_in_val or not check_out_val:
                continue  # Ignorar filas vacías o con datos incompletos

            # --- Lógica de limpieza de datos ---
            employee_name = str(employee_name_raw).strip()
            # Quitar códigos como (12), (3), etc. al final
            employee_name = re.sub(r'\s*\(\d+\)$', '', employee_name).strip()

            employee = employee_cache.get(employee_name)
            if not employee:
                employee = self.env['hr.employee'].search([('name', '=ilike', employee_name)], limit=1)
                if not employee:
                    errors.append(_("Fila %d: Empleado '%s' no encontrado.") % (row_index, employee_name))
                    continue
                employee_cache[employee_name] = employee

            try:
                # Odoo espera datetimes en UTC. openpyxl usualmente devuelve datetimes "naive" (sin zona horaria).
                # Asumimos que las horas en Excel están en la zona horaria del usuario que importa.
                user_tz_str = self.env.user.tz or 'UTC'
                user_tz = pytz.timezone(user_tz_str) if pytz else None

                # Convertir a datetime si no lo es ya
                if not isinstance(check_in_val, datetime):
                    errors.append(_("Fila %d: El valor de 'Entrada' ('%s') no es una fecha/hora válida.") % (row_index,
                                                                                                             check_in_val))
                    continue
                if not isinstance(check_out_val, datetime):
                    errors.append(_("Fila %d: El valor de 'Salida' ('%s') no es una fecha/hora válida.") % (row_index,
                                                                                                            check_out_val))
                    continue

                if user_tz:
                    # Asignar la zona horaria del usuario y luego convertir a UTC
                    check_in_utc = user_tz.localize(check_in_val).astimezone(pytz.utc).replace(tzinfo=None)
                    check_out_utc = user_tz.localize(check_out_val).astimezone(pytz.utc).replace(tzinfo=None)
                else:  # Fallback si pytz no está
                    check_in_utc = check_in_val
                    check_out_utc = check_out_val

                if check_out_utc < check_in_utc:
                    errors.append(_("Fila %d: La Salida no puede ser anterior a la Entrada.") % row_index)
                    continue

                attendances_to_create.append({
                    'employee_id': employee.id,
                    'check_in': check_in_utc,
                    'check_out': check_out_utc,
                })

            except Exception as e:
                errors.append(_("Fila %d: Error procesando fechas - %s") % (row_index, str(e)))

        if not attendances_to_create and errors:
            raise UserError(
                _("No se pudo importar ninguna asistencia. Revise los siguientes errores:\n\n") + "\n".join(errors))

        # Crear los registros
        created_attendances = self.env['hr.attendance']
        for vals in attendances_to_create:
            if self.overwrite_existing:
                domain = [
                    ('employee_id', '=', vals['employee_id']),
                    ('check_in', '>=', vals['check_in'].replace(hour=0, minute=0, second=0)),
                    ('check_in', '<=', vals['check_in'].replace(hour=23, minute=59, second=59)),
                ]
                self.env['hr.attendance'].search(domain).unlink()

            created_attendances |= self.env['hr.attendance'].create(vals)

        final_message = _("¡Importación completada! Se crearon %d registros de asistencia.") % len(created_attendances)
        if errors:
            final_message += _("\n\nSe encontraron las siguientes advertencias:\n") + "\n".join(errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Resultado de la Importación'),
                'message': final_message,
                'sticky': True,  # Para que el usuario pueda leer el mensaje
            }
        }