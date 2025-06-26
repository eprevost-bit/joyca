
{
    'name': 'Login Unsplash Images',
    'version': '18.0',
    'summary': 'It can change images in /web/login',
    'description': """
    This module can chnage images when user refresh the login page.
    """,
    'category': 'website',
    'author': 'Devendra kavthekar',
    "support": "dkatodoo@gmail.com",
    "website": "https://dek-odoo.github.io",
    "license": "OPL-1",
    "images": ["static/description/banner.gif"],
    "price": 0.00,
    "currency": "EUR",

    'depends': ['base','web'],
    'data': [
    ],
    'assets':{
        'web.assets_frontend':[
            'deskent_unsplash_images/static/src/css/style.css',
            'deskent_unsplash_images/static/src/js/login.js',
        ],
    },
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/demo.png'],

}






