# -*- coding: utf-8 -*-
{
    'name': 'Subsections Coton',
    'version': '1.0',
    'summary': 'Brief description of the module',
    'description': '''
        Detailed description of the module
    ''',
    'category': 'Uncategorized',
    'author': 'Unlimioo',
    'company': 'Unlimioo',
    'maintainer': 'Unlimioo',
    'website': 'https://www.Unlimioo.com',
    'depends': ['base', 'sale_management','product'],
    'data': [
        'security/ir.model.access.csv',
        'views/subsections_coton_views.xml',
        'data/product_data.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}