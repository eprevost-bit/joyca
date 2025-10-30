from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    allow_detail_view = fields.Boolean(string='Allow Detailed View')

    print_folded = fields.Boolean(string='Print Folded', default=True,
                                  help="if checked this field will print pdf report in folded state i.e only main products/kits, if uncheck default default report will be printed")


    def _get_order_lines_to_report_task(self):
        lines = self.order_line.filtered(lambda m: m.display_type == 'line_section')
        return lines