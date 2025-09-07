# models/sale_order.py
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo para calcular el total facturado sumando las facturas relacionadas
    amount_invoiced_custom = fields.Monetary(
        string="Total Facturado",
        compute='_compute_amount_invoiced_custom',
        store=True,
        readonly=True
    )

    # Campo para la barra de progreso
    invoice_progress = fields.Float(
        string="Progreso de Facturación (%)",
        compute='_compute_amount_invoiced_custom',
        store=True,
        help="Porcentaje del total del pedido que ya ha sido facturado."
    )

    @api.depends('invoice_ids.state', 'invoice_ids.amount_total_signed', 'amount_total')
    def _compute_amount_invoiced_custom(self):
        for order in self:
            invoices = order.invoice_ids.filtered(lambda inv: inv.state in ['posted', 'paid'])
            order.amount_invoiced_custom = sum(invoices.mapped('amount_total_signed'))
            if order.amount_total > 0:
                order.invoice_progress = (order.amount_invoiced_custom / order.amount_total) * 100
            else:
                order.invoice_progress = 0.0

    # Esta es la acción que abrirá nuestro nuevo asistente
    def action_open_invoice_wizard(self):
        # Creamos las líneas para el asistente
        wizard_lines = []
        for line in self.order_line.filtered(lambda l: not l.display_type):
            wizard_lines.append((0, 0, {
                'sale_order_line_id': line.id,
            }))

        # Creamos el asistente y le pasamos las líneas
        wizard = self.env['sale.line.invoice.wizard'].create({
            'sale_order_id': self.id,
            'wizard_line_ids': wizard_lines,
        })

        # Devolvemos la acción para abrir la vista del asistente
        return {
            'name': 'Crear Factura Parcial por Línea',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.line.invoice.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }