from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

from odoo.http import request, content_disposition
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from odoo import models, fields, api
from datetime import datetime, timedelta, time
import random
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class WebsiteRedirectController(http.Controller):

    @http.route('/', type='http', auth="public", website=True)
    def redirect_to_login(self, **kw):
        if request.env.user._is_public():
            # Redirigir al login de Odoo
            return request.redirect('/web/login')
        else:
            # Si ya está logueado, lo enviamos a su portal
            return request.redirect('/my/home')


class EmployeePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        employee = request.env.user.employee_id
        if employee:
            attendance_count = request.env['hr.attendance'].search_count([
                ('employee_id', '=', employee.id),
            ])
            values['attendance_count'] = attendance_count
        return values

    @http.route(['/my/attendances'], type='http', auth="user", website=True)
    def portal_my_attendances(self, **kw):
        employee = request.env.user.employee_id
        if not employee:
            return request.render("website.404")

        # Configuración de paginación para Últimos Registros
        page = int(kw.get('page', 1))
        recent_page = int(kw.get('recent_page', 1))
        per_page = 7  # 7 registros por página

        # Paginación para Últimos Registros
        total_attendances = request.env['hr.attendance'].search_count([
            ('employee_id', '=', employee.id)
        ])
        offset = (page - 1) * per_page
        attendances = request.env['hr.attendance'].search([
            ('employee_id', '=', employee.id)
        ], order='check_in desc', limit=per_page, offset=offset)

        # Paginación para Registros Recientes (últimos 7 días)
        seven_days_ago = datetime.now() - timedelta(days=7)
        total_recent = request.env['hr.attendance'].search_count([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', seven_days_ago)
        ])
        recent_offset = (recent_page - 1) * per_page
        recent_attendances = request.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', seven_days_ago)
        ], order='check_in desc', limit=per_page, offset=recent_offset)

        # Calcular total de páginas
        total_pages = (total_attendances + per_page - 1) // per_page
        total_recent_pages = (total_recent + per_page - 1) // per_page

        values = {
            'employee': employee,
            'attendances': attendances,
            'recent_attendances': recent_attendances,
            'page_name': 'attendances',
            'today': fields.Date.today(),
            # Paginación Últimos Registros
            'current_page': page,
            'total_pages': total_pages,
            'total_attendances': total_attendances,
            # Paginación Registros Recientes
            'recent_current_page': recent_page,
            'total_recent_pages': total_recent_pages,
            'total_recent': total_recent,
        }
        return request.render("ibec_portal_empleado_instalacion.portal_attendances_template", values)

    @http.route('/my/attendance/clock', type='json', auth="user", website=True)
    def portal_attendance_clock(self, **kw):
        """
        Endpoint JSON para fichar entrada/salida.
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No se encontró el empleado asociado.'}

        try:
            attendance = employee._attendance_action_change()
            action = 'check_in' if not attendance.check_out else 'check_out'

            worked_hours = 0
            if action == 'check_out' and attendance.check_in and attendance.check_out:
                delta = attendance.check_out - attendance.check_in
                worked_hours = delta.total_seconds() / 3600

            return {
                'action': action,
                'attendance_state': employee.attendance_state,
                'check_in_time': attendance.check_in.strftime('%H:%M') if attendance.check_in else '',
                'worked_hours': worked_hours,
                'message': 'Registro exitoso'
            }
        except Exception as e:
            return {
                'error': str(e),
                'attendance_state': employee.attendance_state
            }

    @http.route('/my/attendance/update', type='json', auth="user", website=True)
    def portal_attendance_update(self, attendance_id, new_check_in_date, new_check_in, new_check_out, **kw):
        """
        Endpoint para actualizar registros de asistencia
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No se encontró el empleado asociado.'}

        try:
            attendance = request.env['hr.attendance'].search([
                ('id', '=', attendance_id),
                ('employee_id', '=', employee.id)
            ])

            if not attendance:
                return {'error': 'Registro no encontrado o no pertenece al empleado'}

            # Verificar que el registro no tenga más de 7 días
            if (fields.Date.today() - attendance.check_in.date()).days > 7:
                return {'error': 'Solo puedes modificar registros de los últimos 7 días'}

            # Parsear la nueva fecha y hora
            new_check_in_date = datetime.strptime(new_check_in_date, '%Y-%m-%d').date()
            new_check_in_time = datetime.strptime(new_check_in, '%H:%M').time()
            new_check_in_dt = datetime.combine(new_check_in_date, new_check_in_time)

            # Manejar el check_out (puede ser None)
            new_check_out_dt = False
            if new_check_out:
                new_check_out_time = datetime.strptime(new_check_out, '%H:%M').time()
                new_check_out_dt = datetime.combine(new_check_in_date, new_check_out_time)

            attendance.write({
                'check_in': new_check_in_dt,
                'check_out': new_check_out_dt or False
            })

            return {
                'success': True,
                'worked_hours': attendance.worked_hours,
                'new_date': new_check_in_date.strftime('%d/%m/%Y')
            }
        except ValueError as ve:
            return {'error': f'Formato de fecha/hora inválido: {str(ve)}. Use YYYY-MM-DD para fecha y HH:MM para hora'}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/my/attendance/delete', type='json', auth="user", website=True)
    def portal_attendance_delete(self, attendance_id, **kw):
        """
        Endpoint para eliminar registros de asistencia
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No se encontró el empleado asociado.'}

        try:
            attendance = request.env['hr.attendance'].search([
                ('id', '=', attendance_id),
                ('employee_id', '=', employee.id)
            ])

            if not attendance:
                return {'error': 'Registro no encontrado o no pertenece al empleado'}

            # Verificar que el registro no tenga más de 7 días
            if (fields.Date.today() - attendance.check_in.date()).days > 7:
                return {'error': 'Solo puedes eliminar registros de los últimos 7 días'}

            attendance.unlink()

            return {
                'success': True,
                'message': 'Registro eliminado correctamente'
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/my/attendances/pdf_report', type='http', auth="user", website=True)
    def attendance_pdf_report(self, **kwargs):
        employee = request.env.user.employee_id
        if not employee:
            return request.not_found()

        # Obtener los registros de asistencia
        attendances = request.env['hr.attendance'].search([
            ('employee_id', '=', employee.id)
        ], order='check_in desc')

        # Crear el PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Estilos
        styles = getSampleStyleSheet()
        style_title = styles['Title']
        style_normal = styles['BodyText']

        # Título
        title = Paragraph(f"Registros de Asistencia - {employee.name}", style_title)
        elements.append(title)
        elements.append(Paragraph("<br/>", style_normal))

        # Datos para la tabla
        data = [
            ["Fecha", "Entrada", "Salida", "Duración (horas)"]
        ]

        for att in attendances:
            data.append([
                att.check_in.strftime('%d/%m/%Y') if att.check_in else '',
                att.check_in.strftime('%H:%M:%S') if att.check_in else '',
                att.check_out.strftime('%H:%M:%S') if att.check_out else '',
                "%.2f" % att.worked_hours
            ])

        # Crear tabla
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(table)

        # Generar PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        # Descargar el archivo
        filename = f"registros_asistencia_{employee.name.replace(' ', '_')}.pdf"
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', content_disposition(filename))
        ]
        return request.make_response(pdf, headers=headers)

    @http.route('/my/attendance/manual_entry', type='http', auth="public", website=True, methods=['POST'])
    def portal_attendance_manual_entry(self, **post):
        """
        Endpoint para registro manual de asistencia
        """
        redirect_url = '/my/attendances'
        employee = request.env.user.employee_id

        if not employee:
            return request.redirect(f"{redirect_url}?error=No se encontró el empleado asociado")

        date = post.get('date')
        check_in = post.get('check_in')
        check_out = post.get('check_out')

        try:
            today = fields.Date.today()
            entry_date = fields.Date.to_date(date)

            if entry_date > today:
                return request.redirect(f"{redirect_url}?error=No puedes registrar días futuros")

            if (today - entry_date).days > 7:
                return request.redirect(f"{redirect_url}?error=Solo puedes registrar días de los últimos 7 días")

            existing = request.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', fields.Datetime.to_datetime(date + ' 00:00:00')),
                ('check_in', '<=', fields.Datetime.to_datetime(date + ' 23:59:59'))
            ], limit=1)

            if existing:
                return request.redirect(f"{redirect_url}?error=Ya existe un registro para este día")

            check_in_dt = fields.Datetime.to_datetime(f"{date} {check_in}:00")
            check_out_dt = fields.Datetime.to_datetime(f"{date} {check_out}:00")

            request.env['hr.attendance'].sudo().create({
                'employee_id': employee.id,
                'check_in': check_in_dt,
                'check_out': check_out_dt,
            })

            return request.redirect(f"{redirect_url}?success=Registro manual creado correctamente")

        except ValueError as ve:
            return request.redirect(f"{redirect_url}?error=Formato de fecha/hora inválido")
        except Exception as e:
            return request.redirect(f"{redirect_url}?error=Error al guardar el registro")
    
    # Añade este nuevo método a tu controlador EmployeePortal
    @http.route('/my/attendance/manual_entry_intervals', type='json', auth="user", website=True, methods=['POST'])
    def portal_attendance_manual_intervals(self, date, intervals, **kw):
        """
        Endpoint JSON para registrar múltiples intervalos de asistencia en un día.
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No se encontró el empleado asociado.'}

        try:
            entry_date = fields.Date.to_date(date)
            today = fields.Date.today()

            # Validaciones de seguridad
            if entry_date > today:
                return {'error': 'No puedes registrar días futuros.'}
            if (today - entry_date).days > 7:
                return {'error': 'Solo puedes registrar días de los últimos 7 días.'}

            # --- Clave: Eliminar registros existentes de ese día para evitar duplicados ---
            domain_start = fields.Datetime.to_datetime(f"{date} 00:00:00")
            domain_end = fields.Datetime.to_datetime(f"{date} 23:59:59")
            
            existing_attendances = request.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', domain_start),
                ('check_in', '<=', domain_end)
            ])
            if existing_attendances:
                existing_attendances.sudo().unlink() # Usamos sudo() por si el usuario no tiene permisos de borrado

            # Crear los nuevos registros
            for interval in intervals:
                check_in_str = interval.get('check_in')
                check_out_str = interval.get('check_out')

                if not check_in_str or not check_out_str:
                    continue # Ignorar intervalos vacíos

                check_in_dt = fields.Datetime.to_datetime(f"{date} {check_in_str}:00")
                check_out_dt = fields.Datetime.to_datetime(f"{date} {check_out_str}:00")

                request.env['hr.attendance'].sudo().create({
                    'employee_id': employee.id,
                    'check_in': check_in_dt,
                    'check_out': check_out_dt,
                })
            
            return {'success': True, 'message': 'Registros guardados correctamente.'}

        except Exception as e:
            _logger.error(f"Error en registro manual de intervalos: {e}")
            return {'error': f'Error al procesar los registros: {e}'}


class AttendanceAutomation(models.Model):
    _name = 'attendance.automation'
    _description = 'Automatización de Registros Horarios'

    @api.model
    def process_weekly_attendance(self):
        # Obtener la fecha del último domingo
        today = fields.Date.today()
        last_sunday = today - timedelta(days=today.weekday() + 1)
        week_start = last_sunday - timedelta(days=6)  # Lunes de la semana pasada

        # Obtener todos los empleados activos
        employees = self.env['hr.employee'].search([('active', '=', True)])

        for employee in employees:
            # Buscar registros de la semana pasada
            existing_attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', week_start),
                ('check_in', '<=', last_sunday)
            ], order='check_in')

            # Archivar registros existentes (marcarlos como archivados)
            existing_attendances.write({'archived': True})

            # Obtener días únicos con registros
            days_with_attendance = set()
            for att in existing_attendances:
                days_with_attendance.add(att.check_in.date())

            # Crear nuevos registros para cada día
            for day in days_with_attendance:
                # Registro mañana
                morning_check_in = datetime.combine(
                    day,
                    time(hour=8, minute=random.randint(55, 65) % 60)
                )
                morning_check_out = datetime.combine(
                    day,
                    time(hour=12, minute=random.randint(55, 65) % 60)
                )

                # Verificar si ya existe un registro en ese rango
                existing_morning = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', morning_check_in - timedelta(minutes=15)),
                    ('check_in', '<=', morning_check_in + timedelta(minutes=15))
                ], limit=1)

                if not existing_morning:
                    try:
                        self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'check_in': morning_check_in,
                            'check_out': morning_check_out,
                            'auto_generated': True
                        })
                    except Exception as e:
                        _logger.error(f"Error creando registro mañana: {str(e)}")

                # Registro tarde
                afternoon_check_in = datetime.combine(
                    day,
                    time(hour=14, minute=random.randint(55, 65) % 60)
                )
                afternoon_check_out = datetime.combine(
                    day,
                    time(hour=17, minute=random.randint(55, 65) % 60)
                )

                # Verificar si ya existe un registro en ese rango
                existing_afternoon = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', afternoon_check_in - timedelta(minutes=15)),
                    ('check_in', '<=', afternoon_check_in + timedelta(minutes=15))
                ], limit=1)

                if not existing_afternoon:
                    try:
                        self.env['hr.attendance'].create({
                            'employee_id': employee.id,
                            'check_in': afternoon_check_in,
                            'check_out': afternoon_check_out,
                            'auto_generated': True
                        })
                    except Exception as e:
                        _logger.error(f"Error creando registro tarde: {str(e)}")
