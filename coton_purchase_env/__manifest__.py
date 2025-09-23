{
    'name': 'Botones Personalizados de Compra',
    'version': '1.0',
    'summary': 'Oculta el botón "Enviar correo electrónico" y añade "Enviar partidas por correo electrónico".',
    'author': 'Tu Nombre',
    'category': 'Purchases',
    'depends': ['purchase'], # Es muy importante indicar la dependencia
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}