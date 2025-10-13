# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ... (aquí van todos los campos que ya tienes en tu clase SaleOrder) ...

    # --- NUEVOS CAMPOS PARA SEGUIMIENTO DE FACTURACIÓN Y COBROS ---

    aggregated_percentage_invoiced = fields.Float(
        string="% Facturado",
        compute='_compute_aggregated_invoice_percentage',
        store=True,
        readonly=True,
        help="Porcentaje facturado ponderado basado en el subtotal de cada línea."
    )

    amount_paid = fields.Monetary(
        string="Importe Cobrado",
        compute='_compute_payment_info',
        store=True,
        readonly=True,
        help="Suma total de los pagos recibidos en las facturas asociadas."
    )

    percentage_paid = fields.Float(
        string="% Cobrado",
        compute='_compute_payment_info',
        store=True,
        readonly=True,
        help="Porcentaje cobrado sobre el total que ha sido facturado."
    )

    @api.depends('order_line.price_subtotal', 'order_line.percentage_invoiced_total')
    def _compute_aggregated_invoice_percentage(self):
        """
        Calcula un promedio ponderado del campo '% Facturado' de las líneas.
        Usa el subtotal de cada línea como peso para que el cálculo sea preciso.
        """
        for order in self:
            if order.amount_untaxed > 0:
                # Tu campo 'percentage_invoiced_total' es una proporción (ej: 0.5).
                # Lo multiplicamos por el subtotal de la línea para ponderarlo.
                weighted_sum = sum(line.percentage_invoiced_total * line.price_subtotal for line in order.order_line)

                # El resultado es la suma ponderada dividida por el total, multiplicado por 100
                # para que el widget 'progressbar' lo muestre correctamente.
                order.aggregated_percentage_invoiced = (weighted_sum / order.amount_untaxed) * 100
            else:
                order.aggregated_percentage_invoiced = 0.0

    @api.depends('invoice_ids.state', 'invoice_ids.amount_total', 'invoice_ids.amount_residual')
    def _compute_payment_info(self):
        """
        Calcula el importe total cobrado y su porcentaje
        basándose en las facturas asociadas al pedido de venta.
        """
        for order in self:
            # Filtramos solo las facturas que han sido confirmadas ("Publicado")
            posted_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')

            if not posted_invoices:
                order.amount_paid = 0.0
                order.percentage_paid = 0.0
                continue

            # El importe cobrado es el total de la factura menos lo que queda por pagar (residual)
            total_invoiced = sum(posted_invoices.mapped('amount_total'))
            amount_paid = total_invoiced - sum(posted_invoices.mapped('amount_residual'))

            order.amount_paid = amount_paid

            if total_invoiced > 0:
                # El porcentaje cobrado se calcula sobre el total que ya ha sido facturado.
                order.percentage_paid = (amount_paid / total_invoiced) * 100
            else:
                order.percentage_paid = 0.0