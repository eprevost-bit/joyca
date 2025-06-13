from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


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

        attendances = request.env['hr.attendance'].search([
            ('employee_id', '=', employee.id)
        ], order='check_in desc', limit=20)

        values = {
            'employee': employee,
            'attendances': attendances,
            'page_name': 'attendances',
        }
        return request.render("ibec_portal_empleado.portal_attendances_template", values)

    @http.route('/my/attendance/clock', type='json', auth="user", website=True)
    def portal_attendance_clock(self, **kw):
        """
        Endpoint JSON para fichar entrada/salida.
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No se encontró el empleado asociado.'}

        try:
            # La función _attendance_action_change devuelve un registro de hr.attendance
            attendance = employee._attendance_action_change()

            # Determinar si fue una entrada o salida
            action = 'check_in' if attendance.check_out is None else 'check_out'

            return {
                'action': action,
                'attendance_state': employee.attendance_state,
                'message': 'Registro exitoso'
            }
        except Exception as e:
            return {
                'error': str(e),
                'attendance_state': employee.attendance_state
            }

    @http.route('/my/attendance/update', type='json', auth="user", website=True)
    def portal_attendance_update(self, attendance_id, new_check_in, new_check_out, **kw):
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

            attendance.write({
                'check_in': new_check_in,
                'check_out': new_check_out
            })

            return {
                'success': True,
                'worked_hours': attendance.worked_hours
            }
        except Exception as e:
            return {'error': str(e)}