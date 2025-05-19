# -*- coding: utf-8 -*-
# from odoo import http


# class SaleMrp(http.Controller):
#     @http.route('/sale_mrp/sale_mrp', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_mrp/sale_mrp/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_mrp.listing', {
#             'root': '/sale_mrp/sale_mrp',
#             'objects': http.request.env['sale_mrp.sale_mrp'].search([]),
#         })

#     @http.route('/sale_mrp/sale_mrp/objects/<model("sale_mrp.sale_mrp"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_mrp.object', {
#             'object': obj
#         })

