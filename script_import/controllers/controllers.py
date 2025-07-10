# -*- coding: utf-8 -*-
# from odoo import http


# class ScriptImport(http.Controller):
#     @http.route('/script_import/script_import', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/script_import/script_import/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('script_import.listing', {
#             'root': '/script_import/script_import',
#             'objects': http.request.env['script_import.script_import'].search([]),
#         })

#     @http.route('/script_import/script_import/objects/<model("script_import.script_import"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('script_import.object', {
#             'object': obj
#         })

