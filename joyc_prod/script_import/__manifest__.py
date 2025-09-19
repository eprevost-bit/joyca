{
    'name': 'Importador de Productos desde Excel',
    'version': '1.0',
    'summary': 'Asistente para importar productos y tarifas desde un archivo Excel.',
    'author': 'Tu Nombre',
    'category': 'Sales/Sales',
    # Dependemos de Ventas para los menús y listas de precios
    'depends': ['sale_management', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_import_wizard_view.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
