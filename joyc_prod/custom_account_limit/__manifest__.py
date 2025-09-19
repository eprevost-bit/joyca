# __manifest__.py
{
    'name': 'Extender Límite de Líneas de Factura',
    'version': '1.0',
    'summary': 'Muestra todas las líneas de factura eliminando la paginación.',
    'description': """
        Este módulo modifica la vista de formulario de las facturas (account.move)
        para aumentar el límite de las líneas de factura visibles a 9999,
        eliminando efectivamente la paginación.
    """,
    'author': 'Tu Nombre',
    'category': 'Accounting/Accounting',
    'depends': ['account'], # Dependencia del módulo de contabilidad
    'data': [
        'views/account_move_view.xml', # Ruta a nuestro archivo de vista
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}