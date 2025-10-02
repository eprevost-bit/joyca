# -*- coding: utf-8 -*-
{
    'name': "JOYCA - Importación de Asistencias Excel",
    'summary': """
        Módulo para importar registros de asistencia (hr.attendance) desde un archivo Excel
        en Odoo 18.
    """,
    'description': """
        Este módulo proporciona una funcionalidad para subir un archivo Excel que contenga
        los datos de entrada y salida de los empleados. Automáticamente crea registros
        de asistencia y calcula las horas trabajadas.
        Características:
        - Asistente para seleccionar y subir archivos Excel.
        - Mapeo de columnas 'Empleado', 'Entrada', 'Salida'.
        - Búsqueda de empleados por nombre.
        - Validación de datos y manejo de errores.
        - Opción para sobrescribir asistencias existentes para el mismo empleado/día.
    """,
    'author': "Tu Nombre/Empresa",
    'website': "http://www.yourcompany.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['base', 'hr_attendance', 'hr'], # 'hr' es necesario para el modelo hr.employee
    'data': [
        'security/ir.model.access.csv',
        'wizards/attendance_import_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}