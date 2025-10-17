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
    'depends': ['sale_management', 'project'], # Dependencia del módulo de ventas

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/project_form_view.xml',
        'views/downpayment_concept_views.xml',
        'views/sale_advance_payment_inv_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}