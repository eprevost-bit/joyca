# -*- coding: utf-8 -*-
{
    'name': "Expand/Collapse One2Many Sections in Odoo",

    'summary': """
        Widget to expand/collapse One2Many Sections in Odoo.
        This widget will inherit existing one2many widget 'section_and_note_one2many' 
        and add a new functionality to expand and collapse sections in one2many field.
        This could be added to any existing one2many field or to any new one2many field with section_and_note_one2many widget
        """,

    'description': """
        Widget to expand/collapse One2Many Sections in Odoo.
        This widget will inherit existing one2many widget 'section_and_note_one2many' 
        and add a new functionality to expand and collapse sections in one2many field.
        This could be added to any existing one2many field or to any new one2many field with section_and_note_one2many widget
    """,

    'author': "Mediod Consulting",
    'website': "https://www.mediodconsulting.com",
    # for the full list
    'category': 'Sale & Manufacturing',
    'version': '18.1',

    # any module necessary for this one to work correctly
    'depends': ['web','sale_management'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order.xml',
        'views/sale_portal_templates.xml',
        'report/sale_report_templates.xml',
    ],


    'assets': {
        'web.assets_backend': [
            'md_widget_expand_collapse_sections/static/src/scss/so_lines_portal.scss',
            'md_widget_expand_collapse_sections/static/src/scss/so_lines.scss',
            'md_widget_expand_collapse_sections/static/src/components/**/*',

        ],
        'web.assets_frontend': [
            'md_widget_expand_collapse_sections/static/src/scss/so_lines_portal.scss',
            'md_widget_expand_collapse_sections/static/src/scss/so_lines.scss',
            'md_widget_expand_collapse_sections/static/src/js/sale_portal_products.js',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
    ],

    "license": "OPL-1",

    'application': True,
    'price': 50.00,
    'currency': 'EUR',
    "images": ['static/description/Banner.png'],
}

