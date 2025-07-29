# -*- coding: utf-8 -*-
# from odoo import http


# class SaleJoyca(http.Controller):
#     @http.route('/sale_joyca/sale_joyca', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_joyca/sale_joyca/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_joyca.listing', {
#             'root': '/sale_joyca/sale_joyca',
#             'objects': http.request.env['sale_joyca.sale_joyca'].search([]),
#         })

#     @http.route('/sale_joyca/sale_joyca/objects/<model("sale_joyca.sale_joyca"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_joyca.object', {
#             'object': obj
#         })

