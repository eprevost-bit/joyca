# -*- coding: utf-8 -*-
{
    'name': "Reporte de Presupuesto Personalizado",

    'summary': """
        Añade una opción para imprimir un reporte de presupuesto de ventas
        con un formato de portada, términos, resumen y detalle.""",

    'description': """
        Este módulo crea un nuevo formato de impresión para las cotizaciones (Sale Order)
        siguiendo un diseño específico. No reemplaza el reporte original.
    """,

    'author': "Tu Nombre Aquí",
    'website': "https://www.tuempresa.com",

    # Categoria del módulo
    'category': 'Sales',
    'version': '1.0',

    # Dependencias: nuestro módulo necesita el módulo de Ventas ('sale_management') para funcionar
    'depends': ['sale_management', 'sale'],

    # Los archivos XML que se cargarán
    'data': [
        'report/sale_report_actions.xml',
        'report/report_layout_custom.xml',
		# 'views/mail_template_views.xml',
		# 'views/mail_template_data.xml',
],
    'installable': True,
    'application': False,
    'auto_install': False,
}