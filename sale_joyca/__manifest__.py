# -*- coding: utf-8 -*-
{
    'name': "Sale Custom State",

    'summary': """
        Adds a new 'Version' state to Sale Orders.""",

    'description': """
        This module extends the sale.order model to add a new custom state called 'Version' 
        and updates the corresponding list view to make it visible.
    """,

    'author': "Tu Nombre",
    'website': "https://www.tuweb.com",

    'category': 'Sales',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_management', 'sale', 'project'], # Dependencia del módulo de ventas

    # always loaded
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}