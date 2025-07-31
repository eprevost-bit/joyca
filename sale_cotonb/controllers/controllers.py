# -*- coding: utf-8 -*-
# from odoo import http


# class SaleCotonb(http.Controller):
#     @http.route('/sale_cotonb/sale_cotonb', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_cotonb/sale_cotonb/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_cotonb.listing', {
#             'root': '/sale_cotonb/sale_cotonb',
#             'objects': http.request.env['sale_cotonb.sale_cotonb'].search([]),
#         })

#     @http.route('/sale_cotonb/sale_cotonb/objects/<model("sale_cotonb.sale_cotonb"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_cotonb.object', {
#             'object': obj
#         })

