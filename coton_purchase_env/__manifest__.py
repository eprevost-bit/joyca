{
    'name': 'Botones Personalizados de Compra',
    'version': '1.0',
    'summary': 'Oculta el botón "Enviar correo electrónico" y añade "Enviar partidas por correo electrónico".',
    'author': 'Tu Nombre',
    'category': 'Purchases',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
        'data/mail_template_data.xml',
		'views/purchase_order_line.xml',
],
    'installable': True,
    'application': False,
    'auto_install': False,
}