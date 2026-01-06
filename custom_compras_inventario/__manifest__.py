{
    "name": "Compras e Inventario Personalizado",
    "version": "1.0",
    "category": "Purchases",
    "summary": "Personalizaciones para los módulos de Compras e Inventario",
    "description": """
Este módulo permite personalizar el comportamiento de:
- Órdenes de compra
- Recepciones de inventario
""",
    "author": "Dayloc",
    "depends": [
        "purchase",
        "stock",
        "project",
        "account"
    ],
'assets': {
    'web.assets_backend': [
        'custom_compras_inventario/static/src/css/center_project_column.css',
    ],
},
    "data": [
        "views/orden_compra_view.xml",
        "views/inventario_view.xml"
    ],
    "installable": True,
    "application": False
}
