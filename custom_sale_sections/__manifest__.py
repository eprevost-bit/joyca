
{
    'name': 'Personalización de Secciones de Venta',
    'version': '18.0.1.0.0',
    'summary': 'Añade un botón para crear secciones estructuradas y calcula costes porcentuales.',
    'author': 'Tu Nombre',
    'category': 'Sales/Sales',
    'depends': ['sale_management', 'sale', 'mail', 'project'], 
    'data': [
        'views/sale_order_view.xml',
        'views/proyect_view.xml',
    ],
    'installable': True,
    'application': False,
}   