# -*- coding: utf-8 -*-
{
    'name': "Attendance Approval Color",
    'summary': """
        Adds colors to Attendance Gantt view based on existing overtime status.
    """,
    'description': """
        - Adds a computed color field based on the existing 'overtime_status' field in hr.attendance.
        - The Gantt view will use this color field for visual representation.
    """,
    'author': "Tu Nombre",
    'website': "https://www.unlimioo.odoo.com",
    'category': 'Human Resources/Attendances',
    'version': '18.0.1.0.0',
    'depends': ['hr_attendance'],
    'data': [
        # Quita esta línea: 'views/hr_attendance_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}