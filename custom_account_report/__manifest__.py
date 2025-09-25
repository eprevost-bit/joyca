# -*- coding: utf-8 -*-
{
    'name': "Reporte de Presupuesto Personalizado",

    'summary': """
        Añade una opción para imprimir un reporte de presupuesto de ventas
        con un formato de portada, términos, resumen y detalle.""",

    'description': """
        Este módulo crea un nuevo formato de impresión para las cotizaciones (Account Move)
        siguiendo un diseño específico. No reemplaza el reporte original.
    """,

    'author': "Tu Nombre Aquí",
    'website': "https://www.tuempresa.com",

    # Categoria del módulo
    'category': 'Accounting',
    'version': '1.0',

    # Dependencias: nuestro módulo necesita el módulo de Ventas ('sale_management') para funcionar
    'depends': ['sale_management', 'sale', 'account'],

    # Los archivos XML que se cargarán
    'data': [
        # 'report/sale_report_layout.xml',
        # 'report/sale_report_template.xml',
        'report/sale_report_actions.xml',
        # 'report/report_sale_order_aclaraciones.xml',
        'report/account_report.xml',
        'report/account_report_all.xml',
    ],

    'assets': {
        'web.report_assets_pdf': [
            'custom_sale_report/static/src/scss/custom_fonts.scss',
            'custom_sale_report/static/src/scss/custom_sale_report.scss',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}