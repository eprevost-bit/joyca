from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class EmployeePortal(CustomerPortal):

    # Sobrescribimos esta función para añadir nuestros contadores al portal principal
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        # Contaremos los fichajes del mes actual
        employee = request.env.user.employee_id
        if employee:
            attendance_count = request.env['hr.attendance'].search_count([
                ('employee_id', '=', employee.id),
            ])
            values['attendance_count'] = attendance_count
        return values

    @http.route(['/my/attendances'], type='http', auth="user", website=True)
    def portal_my_attendances(self, **kw):
        """
        Ruta principal para la página de registro horario del empleado.
        """
        employee = request.env.user.employee_id
        if not employee:
            # Si el usuario no es un empleado, redirigir o mostrar error
            return request.render("website.404")

        attendances = request.env['hr.attendance'].search([
            ('employee_id', '=', employee.id)
        ], order='check_in desc', limit=20) # Mostramos los últimos 20 fichajes

        values = {
            'employee': employee,
            'attendances': attendances,
            'page_name': 'attendances', # para marcar el menú como activo
        }
        return request.render("ibec_portal_empleado.portal_attendances_template", values)

    @http.route('/my/attendance/clock', type='json', auth="user", website=True)
    def portal_attendance_clock(self, **kw):
        """
        Endpoint JSON para fichar entrada/salida.
        Reutiliza la lógica estándar de Odoo.
        """
        employee = request.env.user.employee_id
        if not employee:
            return {'error': 'No se encontró el empleado asociado.'}

        # Llama a la función estándar de Odoo que gestiona el fichaje
        res = employee._attendance_action_change()

        # Devolvemos el nuevo estado para que el frontend se actualice
        return {
            'action': res.get('action'),
            'attendance_state': employee.attendance_state,
        }