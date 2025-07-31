# -*- coding: utf-8 -*-
{
    'name': "Flujo de Estados Personalizado para Ventas",
    'summary': """
        Agrega un nuevo flujo de estados para los pedidos de venta:
        Borrador, A la espera de compras, Listo para enviar, Enviado, Confirmado.""",
    'description': """
        Este módulo introduce un campo de estado personalizado y botones para gestionar un flujo de trabajo específico en los presupuestos y pedidos de venta.
    """,
    'author': "Tu Nombre",
    'website': "https://www.tuweb.com",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': [
        'sale_management',
        'sale',
        'purchase'
    ],
    'data': [
        # 'security/ir.model.access.csv', # No es necesario para este ejemplo
        'views/sale_order_view.xml',  # Cargamos nuestro archivo de vista
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}