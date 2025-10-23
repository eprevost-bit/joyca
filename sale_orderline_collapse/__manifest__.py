{
    'name': 'Sale Order Line Collapse',
    'version': '18.0.1.0.0',
    'summary': 'Collapse / Expand One2many lines on Sale Order',
    'category': 'Sales',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_orderline_collapse/static/src/js/collapse_one2many.js',
        ],
    },
    'installable': True,
    'application': True,
}
