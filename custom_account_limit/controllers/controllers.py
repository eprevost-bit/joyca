# -*- coding: utf-8 -*-
# from odoo import http


# class CustomSaleSections(http.Controller):
#     @http.route('/custom_sale_sections/custom_sale_sections', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_sale_sections/custom_sale_sections/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_sale_sections.listing', {
#             'root': '/custom_sale_sections/custom_sale_sections',
#             'objects': http.request.env['custom_sale_sections.custom_sale_sections'].search([]),
#         })

#     @http.route('/custom_sale_sections/custom_sale_sections/objects/<model("custom_sale_sections.custom_sale_sections"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_sale_sections.object', {
#             'object': obj
#         })

