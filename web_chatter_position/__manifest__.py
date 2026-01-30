

{
    "name": "Chatter Position",
    "summary": "Add an option to change the chatter position",
    "version": "18.0.1.0.1",

    "maintainers": ["trisdoan"],
    "license": "LGPL-3",
    "category": "Extra Tools",
    "depends": ["web", "mail"],
    "data": ["views/res_users.xml", "views/web.xml"],
    "assets": {
        "web.assets_backend": [
            "/web_chatter_position/static/src/**/*.js",
            "/web_chatter_position/static/src/**/*.scss",
        ],
    },
}
