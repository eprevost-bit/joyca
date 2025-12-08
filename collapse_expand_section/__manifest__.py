{
    'name': 'Collapse Expand Section on One2many Field',
    'summary': "Collapse Expand Section on One2many Field. Show total items under section line. Sale Order Lines | Purchase Order Lines | Invoice Lines | Bill Lines",
    'description': "Collapse Expand Section on One2many Field. Show total items under section line.",
    'author': "Sonny Huynh",
    'category': 'Productivity',
    'version': '18.0.0.1',
    'depends': ['web', 'account', 'sale'],

    'data': [],

    'assets': {
        'web.assets_backend': [
            'collapse_expand_section/static/src/js/components/sale_product_field.js',
            'collapse_expand_section/static/src/js/components/section_and_note_fields_backend.xml',
            'collapse_expand_section/static/src/js/components/section_note_fields_backend.js',
        ],
    },

    'images': [
        'static/description/banner.gif',
    ],
    'license': 'OPL-1',
    'price': 80.00,
    'currency': 'EUR',
}