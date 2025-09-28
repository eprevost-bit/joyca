from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.tools.misc import file_open
import base64
import io


from odoo.http import request, content_disposition
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from odoo import models, fields, api
from datetime import datetime, timedelta, time
import random
from dateutil.relativedelta import relativedelta
import logging
import pytz
from odoo.tools import format_time

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
        seven_days_ago = datetime.now() - timedelta(days=15)
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

    # En tu archivo de controllers (portal.py)

    @http.route('/my/attendance/clock', type='json', auth="user", website=True)
    def portal_attendance_clock(self, **kw):
        """
        Endpoint JSON para fichar entrada/salida.
        --- VERSIÓN MEJORADA CON CÁLCULO DE HORAS TRABAJADAS ---
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No se encontró el empleado asociado.'}

        previous_state = employee.attendance_state

        try:
            attendance = employee._attendance_action_change()
            action = 'check_in' if attendance.check_in and not attendance.check_out else 'check_out'

            user_tz = request.env.user.tz or 'UTC'
            local_tz = pytz.timezone(user_tz)
            formatted_time_str = ''

            if action == 'check_in' and attendance.check_in:
                local_time = pytz.utc.localize(attendance.check_in).astimezone(local_tz)
                formatted_time_str = local_time.strftime('%H:%M:%S')
            elif action == 'check_out' and attendance.check_out:
                local_time = pytz.utc.localize(attendance.check_out).astimezone(local_tz)
                formatted_time_str = local_time.strftime('%H:%M:%S')

            response = {
                'success': True,
                'action': action,
                'employee_name': employee.name,
                'formatted_time': formatted_time_str,
            }

            # === INICIO DE LA MODIFICACIÓN ===
            # Si la acción es de salida, calcula y añade las horas trabajadas a la respuesta.
            if action == 'check_out':
                response['worked_hours'] = attendance.worked_hours
            # === FIN DE LA MODIFICACIÓN ===

            _logger.info(f"Portal Attendance Clock Success: {response}")
            return response

        except Exception as e:
            _logger.error(f"Error en portal_attendance_clock: {str(e)}")
            return {
                'error': str(e),
                'previous_state': previous_state
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

        # --- FILTRO: OBTENER Y VALIDAR FECHAS ---
        start_date_str = kwargs.get('start_date')
        end_date_str = kwargs.get('end_date')
        domain = [('employee_id', '=', employee.id)]
        date_title_part = ""

        try:
            if start_date_str:
                start_date = fields.Date.to_date(start_date_str)
                domain.append(('check_in', '>=', start_date))

            if end_date_str:
                end_date = fields.Date.to_date(end_date_str)
                domain.append(('check_in', '<=', fields.Datetime.end_of(end_date, 'day')))

            if start_date_str and end_date_str:
                date_title_part = f" ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})"
            elif start_date_str:
                date_title_part = f" (Desde {start_date.strftime('%d/%m/%Y')})"
            elif end_date_str:
                date_title_part = f" (Hasta {end_date.strftime('%d/%m/%Y')})"

        except Exception as e:
            _logger.warning(f"Formato de fecha inválido para el reporte PDF: {e}")
            pass

        # --- BÚSQUEDA DE REGISTROS CON EL FILTRO APLICADO ---
        attendances = request.env['hr.attendance'].search(domain, order='check_in desc')

        # --- INICIO DE LA CREACIÓN DEL PDF ---
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=inch / 2, leftMargin=inch / 2, topMargin=inch / 2,
                                bottomMargin=inch / 2)
        elements = []
        styles = getSampleStyleSheet()

        # --- ENCABEZADO: OBTENER DATOS DE LA COMPAÑÍA ---
        company = request.env.user.company_id

        # --- ENCABEZADO: PREPARAR EL LOGO ---
        logo_image = False
        if company.logo:
            image_data = base64.b64decode(company.logo)
            image_in_memory = io.BytesIO(image_data)
            img = Image(image_in_memory, width=1.0 * inch, height=1.0 * inch, kind='proportional')
            logo_image = img
        if not logo_image:
            logo_image = Paragraph("Sin Logo", styles['Normal'])

        # --- ENCABEZADO: PREPARAR LA DIRECCIÓN ---
        address_style = ParagraphStyle(
            name='AddressStyle', parent=styles['Normal'], fontSize=9, leading=11, alignment=2
        )
        company_details = []
        if company.name: company_details.append(f"<b>{company.name}</b>")
        if company.street: company_details.append(company.street)
        if company.city or company.state_id or company.zip: company_details.append(
            f"{company.city or ''}, {company.state_id.name or ''} {company.zip or ''}")
        if company.country_id: company_details.append(company.country_id.name)
        if company.phone: company_details.append(f"Tel: {company.phone}")
        if company.website: company_details.append(company.website)
        address_paragraph = Paragraph("<br/>".join(company_details), address_style)

        # --- ENCABEZADO: CREAR LA TABLA DEL ENCABEZADO Y AÑADIRLA AL PDF ---
        header_data = [[logo_image, address_paragraph]]
        header_table = Table(header_data, colWidths=[1.2 * inch, 6.3 * inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.25 * inch))

        # --- TÍTULO DINÁMICO DEL REPORTE ---
        style_title = styles['Title']
        report_title = f"Registros de Asistencia - {employee.name}{date_title_part}"
        title = Paragraph(report_title, style_title)
        elements.append(title)
        elements.append(Paragraph("<br/>", styles['Normal']))

        # --- TABLA DE REGISTROS ---
        data = [
            ["Fecha", "Entrada", "Salida", "Duración (horas)", "Estado"]
        ]
        status_map = {'to_approve': 'A Aprobar', 'approved': 'Aprobado', 'refused': 'Rechazado'}
        for att in attendances:
            status_text = status_map.get(att.overtime_status, '')
            data.append([
                att.check_in.strftime('%d/%m/%Y') if att.check_in else '',
                att.check_in.strftime('%H:%M:%S') if att.check_in else '',
                att.check_out.strftime('%H:%M:%S') if att.check_out else '',
                "%.2f" % att.worked_hours,
                status_text
            ])

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

        # --- FINALIZACIÓN Y DESCARGA DEL PDF ---
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

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

    @http.route('/my/attendance/manual_entry_intervals', type='json', auth="user", website=True, methods=['POST'])
    def portal_attendance_manual_intervals(self, date, intervals, **kw):
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No se encontró el empleado asociado.'}
        try:
            entry_date = fields.Date.to_date(date)
            today = fields.Date.today()
            if entry_date > today:
                return {'error': 'No puedes registrar días futuros.'}
            if (today - entry_date).days > 7:
                return {'error': 'Solo puedes registrar días de los últimos 7 días.'}
            domain_start = fields.Datetime.to_datetime(f"{date} 00:00:00")
            domain_end = fields.Datetime.to_datetime(f"{date} 23:59:59")
            existing_attendances = request.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', domain_start),
                ('check_in', '<=', domain_end)
            ])
            if existing_attendances:
                existing_attendances.sudo().unlink()
            for interval in intervals:
                check_in_str = interval.get('check_in')
                check_out_str = interval.get('check_out')
                if not check_in_str or not check_out_str:
                    continue
                check_in_dt = fields.Datetime.to_datetime(f"{date} {check_in_str}:00")
                check_out_dt = fields.Datetime.to_datetime(f"{date} {check_out_str}:00")
                if check_in_dt >= check_out_dt:
                    return {
                        'error': f'Intervalo inválido: La entrada ({check_in_str}) no puede ser posterior o igual a la salida ({check_out_str}).'}
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
