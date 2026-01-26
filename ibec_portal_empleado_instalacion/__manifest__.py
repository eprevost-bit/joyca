# in ibec_portal_empleado_instalacion/__manifest__.py

{
    'name': "IBEC Portal del Empleado",
    'summary': """
        Portal para que los empleados fichen, consulten sus horas
        y gestionen su jornada laboral.""",
    'description': """
        - Página privada en el portal para el registro horario (Entrada/Salida).
        - Visualización de registros históricos.
        - Evita el uso de licencias de usuario interno.
    """,
    'author': "Tu Nombre o Empresa",
    'website': "https://www.tuweb.com",
    'category': 'Human Resources/Attendances',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'portal',
        'website',
        'hr_attendance',
        'hr_contract',  # Lo necesitaremos para las horas extra más adelante
    ],
    'data': [
        # 'security/ir.model.access.csv', # Lo añadiremos cuando sea necesario
        'views/portal_templates.xml',
        'views/layout_header.xml',
        'views/hr_attendance_view_form.xml',
        'views/portal_attendances_template.xml',
        'data/cron.xml',
    ],

    # Archivos de assets (JS, CSS)
    'assets': {
        'web.assets_frontend': [
            'ibec_portal_empleado/static/src/js/attendance_portal.js',
            'ibec_portal_empleado/static/src/css/attendance_portal.css',
        ],
    },
    'installable': True,
    'application': False,
}