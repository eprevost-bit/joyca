{
    'name': 'Custom Purchase Quotation Report',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Customizes the Request for Quotation PDF Report',
    'depends': ['purchase'],
    'data': [
        'views/layout.xml',
        'views/report_purchasequotation_custom.xml',
    ],
    'installable': True,
    'application': False,
}
