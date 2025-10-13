# -*- coding: utf-8 -*-

from odoo import models, fields, api

# --- 1. AÑADIR CAMPO CALCULADO A LA LÍNEA DE COMPRA ---

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    percentage_invoiced = fields.Float(
        string="% Facturado",
        compute='_compute_percentage_invoiced',
        store=True,
        readonly=True,
        help="Porcentaje de la cantidad de esta línea que ha sido facturada por el proveedor."
    )

    @api.depends('qty_invoiced', 'product_qty')
    def _compute_percentage_invoiced(self):
        """
        Calcula la PROPORCIÓN (0.0 a 1.0) que ha sido facturada.
        El widget se encargará de mostrarlo como porcentaje.
        """
        for line in self:
            if line.product_qty > 0:
                # Guardamos el valor como una fracción (ej: 0.8 para 80%)
                line.percentage_invoiced = line.qty_invoiced / line.product_qty
            else:
                line.percentage_invoiced = 0.0


# --- 2. AÑADIR CAMPOS AGREGADOS A LA ORDEN DE COMPRA ---

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    aggregated_percentage_invoiced = fields.Float(
        string="% Facturado",
        compute='_compute_aggregated_invoice_percentage',
        store=True,
        readonly=True,
        help="Porcentaje facturado ponderado basado en el subtotal de cada línea."
    )

    amount_paid = fields.Monetary(
        string="Importe Pagado",
        compute='_compute_payment_info',
        store=True,
        readonly=True,
        help="Suma total de los pagos realizados en las facturas de proveedor asociadas."
    )

    percentage_paid = fields.Float(
        string="% Pagado",
        compute='_compute_payment_info',
        store=True,
        readonly=True,
        help="Porcentaje pagado sobre el total que ha sido facturado."
    )

    @api.depends('order_line.price_subtotal', 'order_line.percentage_invoiced')
    def _compute_aggregated_invoice_percentage(self):
        """
        Calcula un promedio ponderado del campo '% Facturado' de las líneas de compra.
        """
        for order in self:
            if order.amount_untaxed > 0:
                weighted_sum = sum(line.percentage_invoiced * line.price_subtotal for line in order.order_line)
                order.aggregated_percentage_invoiced = (weighted_sum / order.amount_untaxed) * 100
            else:
                order.aggregated_percentage_invoiced = 0.0

    @api.depends('invoice_ids.state', 'invoice_ids.amount_total', 'invoice_ids.amount_residual')
    def _compute_payment_info(self):
        """
        Calcula el importe total pagado y su porcentaje
        basándose en las facturas de proveedor asociadas.
        """
        for order in self:
            # Filtramos solo facturas de proveedor ('in_invoice') que están publicadas
            posted_bills = order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'in_invoice' and inv.state == 'posted'
            )

            if not posted_bills:
                order.amount_paid = 0.0
                order.percentage_paid = 0.0
                continue

            total_billed = sum(posted_bills.mapped('amount_total'))
            amount_paid = total_billed - sum(posted_bills.mapped('amount_residual'))

            order.amount_paid = amount_paid

            if total_billed > 0:
                order.percentage_paid = (amount_paid / total_billed) * 100
            else:
                order.percentage_paid = 0.0