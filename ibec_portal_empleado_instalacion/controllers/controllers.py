from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime, timedelta,time
import logging

_logger = logging.getLogger(__name__)


class WebsiteRedirectController(http.Controller):

    @http.route('/', type='http', auth="public", website=True)
    def redirect_to_login(self, **kw):
        if request.env.user._is_public():
            return request.redirect('/web/login')
        return request.redirect('/my/home')


class EmployeePortal(CustomerPortal):


    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        employee = request.env.user.employee_id
        Attendance = request.env['hr.attendance'].sudo()

        has_open_attendance = False
        has_today_attendance = False

        if employee:

            has_open_attendance = Attendance.search_count([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False),
            ]) > 0


            today = fields.Date.today()
            has_today_attendance = Attendance.search_count([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', today),
                ('check_in', '<', today + timedelta(days=1)),
            ]) > 0

            values['attendance_count'] = Attendance.search_count([
                ('employee_id', '=', employee.id)
            ])

        values.update({
            'employee': employee,
            'has_open_attendance': has_open_attendance,
            'has_today_attendance': has_today_attendance,
        })

        return values


    @http.route(['/my/attendances'], type='http', auth="user", website=True)
    def portal_my_attendances(self, **kw):
        employee = request.env.user.employee_id
        if not employee:
            return request.render("website.404_plausible")

        Attendance = request.env['hr.attendance']

        page = int(kw.get('page', 1))
        recent_page = int(kw.get('recent_page', 1))
        per_page = 7


        total_attendances = Attendance.search_count([
            ('employee_id', '=', employee.id)
        ])

        attendances = Attendance.search(
            [('employee_id', '=', employee.id)],
            order='check_in desc',
            limit=per_page,
            offset=(page - 1) * per_page
        )


        fifteen_days_ago = datetime.now() - timedelta(days=15)

        total_recent = Attendance.search_count([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', fifteen_days_ago)
        ])

        recent_attendances = Attendance.search(
            [
                ('employee_id', '=', employee.id),
                ('check_in', '>=', fifteen_days_ago)
            ],
            order='check_in desc',
            limit=per_page,
            offset=(recent_page - 1) * per_page
        )


        has_open_attendance = Attendance.search_count([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ]) > 0

        # 🟢 Registro hoy
        today = fields.Date.today()
        has_today_attendance = Attendance.search_count([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', today),
            ('check_in', '<', today + timedelta(days=1)),
        ]) > 0

        return request.render("ibec_portal_empleado.portal_attendances_template", {
            'employee': employee,
            'attendances': attendances,
            'recent_attendances': recent_attendances,

            'page_name': 'attendances',
            'current_page': page,
            'recent_current_page': recent_page,
            'total_pages': (total_attendances + per_page - 1) // per_page,
            'total_recent_pages': (total_recent + per_page - 1) // per_page,

            'has_open_attendance': has_open_attendance,
            'has_today_attendance': has_today_attendance,
        })


    @http.route('/my/attendance/clock', type='json', auth='user', website=True)
    def portal_attendance_clock(self):
        employee = request.env.user.employee_id.sudo()
        if not employee:
            return {'error': 'Tu usuario no está vinculado a un empleado.'}

        Attendance = request.env['hr.attendance'].sudo()
        now = fields.Datetime.now()
        open_attendance = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], limit=1)

        if open_attendance:
            open_attendance.write({'check_out': now})
            return {
                'action': 'check_out',
                'state': 'checked_out',
                'employee_name': employee.name,
                'formatted_time': now.strftime('%H:%M'),
                'worked_hours': open_attendance.worked_hours or 0.0,
            }

        Attendance.create({
            'employee_id': employee.id,
            'check_in': now,
        })

        return {
            'action': 'check_in',
            'state': 'checked_in',
            'employee_name': employee.name,
            'formatted_time': now.strftime('%H:%M'),
        }


    @http.route('/my/attendance/update', type='json', auth="user", website=True)
    def portal_attendance_update(self, attendance_id, new_check_in_date, new_check_in, new_check_out):
        employee = request.env.user.employee_id
        Attendance = request.env['hr.attendance'].sudo()

        attendance = Attendance.search([
            ('id', '=', attendance_id),
            ('employee_id', '=', employee.id)
        ], limit=1)

        if not attendance:
            return {'error': 'Registro no válido.'}

        if (fields.Date.today() - attendance.check_in.date()).days > 7:
            return {'error': 'Solo puedes modificar registros de los últimos 7 días.'}

        try:

            date = datetime.strptime(new_check_in_date, '%Y-%m-%d').date()
            check_in_dt = datetime.combine(
                date,
                datetime.strptime(new_check_in, '%H:%M').time()
            )

            check_out_dt = False
            if new_check_out:
                check_out_dt = datetime.combine(
                    date,
                    datetime.strptime(new_check_out, '%H:%M').time()
                )


            if check_out_dt and check_in_dt >= check_out_dt:
                return {'error': 'La hora de entrada debe ser menor que la de salida.'}


            if check_out_dt:
                overlap = Attendance.search([
                    ('employee_id', '=', employee.id),
                    ('id', '!=', attendance.id),
                    ('check_in', '<', check_out_dt),
                    ('check_out', '>', check_in_dt),
                ], limit=1)

                if overlap:
                    return {
                        'error': 'El horario se solapa con otro registro existente.'
                    }


            attendance.write({
                'check_in': check_in_dt,
                'check_out': check_out_dt,
            })

            return {
                'success': True,
                'worked_hours': attendance.worked_hours
            }

        except Exception as e:
            _logger.exception(e)
            return {'error': 'Datos inválidos.'}

    @http.route('/my/attendance/delete', type='json', auth="user", website=True)
    def portal_attendance_delete(self, attendance_id):
        attendance = request.env['hr.attendance'].search([
            ('id', '=', attendance_id),
            ('employee_id', '=', request.env.user.employee_id.id)
        ], limit=1)

        if not attendance:
            return {'error': 'Registro no válido.'}

        attendance.unlink()
        return {'success': True}
    """"
    @http.route('/my/attendance/manual_entry_intervals', type='json', auth='user', website=True)
    def portal_attendance_manual_entry_intervals(self, date, intervals):
        employee = request.env.user.employee_id
        Attendance = request.env['hr.attendance'].sudo()

        #bloqueo si hay registro abierto
        open_attendance = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], limit=1)

        if open_attendance:
            return {
                'error': (
                    "No puedes registrar horarios manuales porque tienes "
                    "una jornada abierta. Registra primero la SALIDA."
                )
            }

        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'Usuario sin empleado asociado.'}

        try:
            Attendance = request.env['hr.attendance'].sudo()
            work_date = datetime.strptime(date, '%Y-%m-%d').date()

            # ===============================
            # 1️⃣ Convertir intervalos y validar orden
            # ===============================
            parsed_intervals = []

            for interval in intervals:
                start = datetime.combine(
                    work_date,
                    datetime.strptime(interval['check_in'], '%H:%M').time()
                )
                end = datetime.combine(
                    work_date,
                    datetime.strptime(interval['check_out'], '%H:%M').time()
                )

                if start >= end:
                    return {
                        'error': f'La hora de entrada {interval["check_in"]} debe ser menor que la salida {interval["check_out"]}.'
                    }

                parsed_intervals.append((start, end))

            # ===============================
            # 2️⃣ Validar solapes ENTRE intervalos enviados
            # ===============================
            parsed_intervals.sort(key=lambda x: x[0])

            for i in range(len(parsed_intervals) - 1):
                current_end = parsed_intervals[i][1]
                next_start = parsed_intervals[i + 1][0]

                if current_end > next_start:
                    return {
                        'error': 'Los horarios introducidos se solapan entre sí.'
                    }

            # ===============================
            # 3️⃣ Validar solapes CONTRA BD
            # ===============================
            existing_attendances = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', work_date),
                ('check_in', '<', work_date + timedelta(days=1)),
            ])

            for new_start, new_end in parsed_intervals:
                for att in existing_attendances:
                    existing_start = att.check_in
                    existing_end = att.check_out or att.check_in

                    if not (new_end <= existing_start or new_start >= existing_end):
                        return {
                            'error': 'El horario introducido se solapa con un registro existente.'
                        }

            # ===============================
            # 4️⃣ Crear registros
            # ===============================
            for start, end in parsed_intervals:
                Attendance.create({
                    'employee_id': employee.id,
                    'check_in': start,
                    'check_out': end,
                    'auto_generated': True,
                })

            return {
                'success': True,
                'message': 'Horarios registrados correctamente.'
            }

        except Exception:
            _logger.exception("Error guardando horarios manuales")
            return {'error': 'Error interno al guardar los horarios.'}
    """
    @http.route('/my/attendance/manual_entry_intervals', type='json', auth='user', website=True)
    def manual_entry_intervals(self, date, intervals):
        employee = request.env.user.employee_id
        Attendance = request.env['hr.attendance'].sudo()

        # bloquear si hay jornada abierta
        open_attendance = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], limit=1)

        if open_attendance:
            return {
                'error': 'No puedes registrar horarios manuales mientras tengas una jornada abierta. Registra primero la salida.'
            }

        # bloquear si se solapa con alguna hora
        target_date = fields.Date.from_string(date)
        day_start = datetime.combine(target_date, time.min)
        day_end = datetime.combine(target_date, time.max)

        existing = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '<=', day_end),
            ('check_out', '>=', day_start),
        ])

        for interval in intervals:
            new_in = datetime.combine(target_date, datetime.strptime(interval['check_in'], '%H:%M').time())
            new_out = datetime.combine(target_date, datetime.strptime(interval['check_out'], '%H:%M').time())

            for att in existing:
                if att.check_out and not (new_out <= att.check_in or new_in >= att.check_out):
                    return {
                        'error': 'Los horarios introducidos se solapan con registros existentes.'
                    }

        #  crear registro
        for interval in intervals:
            Attendance.create({
                'employee_id': employee.id,
                'check_in': datetime.combine(target_date, datetime.strptime(interval['check_in'], '%H:%M').time()),
                'check_out': datetime.combine(target_date, datetime.strptime(interval['check_out'], '%H:%M').time()),
                'auto_generated': True,
            })

        return {'success': True, 'message': 'Horarios registrados correctamente.'}
