from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleLineInvoiceWizardLine(models.TransientModel):
    _name = 'sale.line.invoice.wizard.line'
    _description = 'Línea del Asistente para Facturar'

    wizard_id = fields.Many2one('sale.line.invoice.wizard', string="Asistente")
    sale_order_line_id = fields.Many2one('sale.order.line', string="Línea del Pedido", readonly=True)

    # Campos relacionados para mostrar información útil
    product_id = fields.Many2one(related='sale_order_line_id.product_id', readonly=True)
    product_uom_qty = fields.Float(related='sale_order_line_id.product_uom_qty', string="Cantidad Pedida",
                                   readonly=True)
    # qty_invoiced = fields.Float(related='sale_order_line_id.qty_invoiced', string="Cantidad ya Facturada",
    #                             readonly=True)
    percentage_invoiced = fields.Float(
        string="Porcentaje ya Facturado (%)",
        compute='_compute_percentage_invoiced',
        readonly=True
    )

    price_subtotal = fields.Monetary(related='sale_order_line_id.price_subtotal', readonly=True)
    currency_id = fields.Many2one(related='sale_order_line_id.currency_id', readonly=True)

    # ¡El campo clave que el usuario rellenará!
    percentage_to_invoice = fields.Float(string="Porcentaje a Facturar (%)", default=0.0)

    def _check_fields_exist(self):
        # Esto forzará a Odoo a reconocer los campos relacionados
        return True

    @api.depends('sale_order_line_id.qty_invoiced', 'sale_order_line_id.product_uom_qty')
    def _compute_percentage_invoiced(self):
        """
        Calcula el porcentaje de la línea que ya ha sido facturado.
        """
        for line in self:
            sol = line.sale_order_line_id
            # Evitar división por cero si la cantidad pedida es 0
            if sol.product_uom_qty > 0:
                line.percentage_invoiced = (sol.qty_invoiced / sol.product_uom_qty) * 100.0
            else:
                line.percentage_invoiced = 0.0

class SaleLineInvoiceWizard(models.TransientModel):
    _name = 'sale.line.invoice.wizard'
    _description = 'Asistente para Facturar Líneas de Venta por Porcentaje'

    sale_order_id = fields.Many2one('sale.order', string="Pedido de Venta", readonly=True)
    wizard_line_ids = fields.One2many(
        'sale.line.invoice.wizard.line',
        'wizard_id',
        string="Líneas a Facturar"
    )

    @api.model
    def default_get(self, fields_list):
        res = super(SaleLineInvoiceWizard, self).default_get(fields_list)
        context = self._context
        if context.get('active_model') == 'sale.order' and context.get('active_id'):
            sale_order = self.env['sale.order'].browse(context['active_id'])
            res['sale_order_id'] = sale_order.id
            # Create wizard lines for each sale order line
            line_vals = []
            for line in sale_order.order_line.filtered(lambda l: l.product_id.invoice_policy != 'order' and l.qty_to_invoice > 0):
                line_vals.append((0, 0, {
                    'sale_order_line_id': line.id,
                    'percentage_to_invoice': 0.0
                }))
            res['wizard_line_ids'] = line_vals
        return res

    def action_create_invoices_from_wizard(self):
        # Primero, actualizamos las cantidades a facturar en el pedido original
        for line in self.wizard_line_ids:
            if line.percentage_to_invoice < 0 or line.percentage_to_invoice > 100:
                raise UserError("El porcentaje debe estar entre 0 y 100.")

            # qty_to_invoice = line.sale_order_line_id.product_uom_qty * (line.percentage_to_invoice / 100.0)
            qty_to_invoice = line.sale_order_line_id.product_uom_qty * line.percentage_to_invoice

            # Validamos no facturar más de lo permitido
            if qty_to_invoice > (line.sale_order_line_id.product_uom_qty - line.sale_order_line_id.qty_invoiced):
                qty_to_invoice = line.sale_order_line_id.product_uom_qty - line.sale_order_line_id.qty_invoiced

            line.sale_order_line_id.qty_to_invoice = qty_to_invoice

        # Luego, llamamos a la función estándar de Odoo para crear la factura
        return self.sale_order_id._create_invoices(final=False)


