# -*- coding: utf-8 -*-

from odoo import models, fields, api

# --- 1. AÑADIR CAMPO CALCULADO A LA LÍNEA DE COMPRA ---

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    # --- CAMPO NUEVO PARA LA MONEDA ---
    # Necesario para los campos Monetary related
    x_sale_currency_id = fields.Many2one(
        related='x_source_sale_line_id.currency_id',
        readonly=True
    )

    # --- CAMPOS OBTENIDOS DE LA VENTA (CORREGIDOS) ---

    # 1. CORREGIDO: Cambiado de Float a Monetary
    x_sale_paid_amount = fields.Monetary(
        related='x_source_sale_line_id.amount_paid_line',
        string='Importe Pagado (Venta)',
        readonly=True,
        store=True,
        currency_field='x_sale_currency_id'  # Especificar la moneda
    )

    # 2. CORREGIDO: Cambiado de Float a Monetary
    x_sale_line_total = fields.Monetary(
        related='x_source_sale_line_id.price_subtotal',
        string='Total Línea Venta (Base)',
        readonly=True,
        store=True,
        currency_field='x_sale_currency_id'  # Especificar la moneda
    )

    # --- CAMPO CALCULADO (PORCENTAJE) ---
    # 3. Este campo está BIEN como Float, ya que el cómputo
    #    lee los valores Monetary como números (float).
    x_sale_paid_percentage = fields.Float(
        string='Porcentaje Pagado (Venta) %',
        compute='_compute_sale_paid_percentage',
        store=True,
        readonly=True,
        digits=(16, 2)
    )

    @api.depends('x_sale_paid_amount', 'x_sale_line_total')
    def _compute_sale_paid_percentage(self):
        """
        Calcula el porcentaje pagado de la línea de venta origen.
        """
        for line in self:
            # Los campos Monetary se leen como floats dentro de los computes
            if line.x_sale_line_total > 0:
                line.x_sale_paid_percentage = (line.x_sale_paid_amount / line.x_sale_line_total) * 100
            else:
                line.x_sale_paid_percentage = 0.0

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