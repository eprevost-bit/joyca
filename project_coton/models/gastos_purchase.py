# -*- coding: utf-8 -*-

from odoo import models, fields, api

# --- 1. AÑADIR CAMPO CALCULADO A LA LÍNEA DE COMPRA ---

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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

    po_currency_id = fields.Many2one(
        related='order_id.currency_id',
        string="Moneda de Compra",
        readonly=True
    )

    # 2. Importe Total Facturado (Por el Proveedor)
    #    Suma de los subtotales de las líneas de factura de proveedor.
    amount_invoiced = fields.Monetary(
        string='Importe Facturado (Compra)',
        compute='_compute_purchase_payment_amounts',
        store=True,
        readonly=True,
        currency_field='po_currency_id',
        help="Total (sin impuestos) facturado por el proveedor para esta línea."
    )

    # 3. Importe Total Pagado (Al Proveedor)
    #    Suma de los importes pagados prorrateados de las facturas.
    amount_paid = fields.Monetary(
        string='Importe Pagado (Compra)',
        compute='_compute_purchase_payment_amounts',
        store=True,
        readonly=True,
        currency_field='po_currency_id',
        help="Total (sin impuestos) pagado al proveedor por las facturas de esta línea."
    )

    # 4. Porcentaje Pagado (de la Compra)
    #    Este es el campo que has solicitado.
    percentage_paid = fields.Float(
        string='% Pagado (Compra)',
        compute='_compute_purchase_percentage',
        store=True,
        readonly=True,
        digits=(16, 2),
        help="Porcentaje del total de la línea (price_subtotal) que ha sido pagado."
    )

    @api.depends('invoice_lines',
                 'invoice_lines.move_id.state',
                 'invoice_lines.move_id.payment_state',
                 'invoice_lines.move_id.amount_total',
                 'invoice_lines.move_id.amount_residual')
    def _compute_purchase_payment_amounts(self):
        """
        Calcula el importe total facturado y el importe total pagado
        para esta línea de pedido de compra.
        """
        for line in self:
            total_invoiced_amount = 0.0
            total_paid_amount = 0.0

            # Filtramos solo facturas de proveedor (in_invoice) que estén publicadas
            posted_bill_lines = line.invoice_lines.filtered(
                lambda l: l.move_id.state == 'posted' and l.move_id.move_type == 'in_invoice'
            )

            for bill_line in posted_bill_lines:
                bill = bill_line.move_id

                # 1. Sumar el total facturado (base)
                #    Usamos 'price_subtotal' de la línea de factura
                total_invoiced_amount += bill_line.price_subtotal

                # 2. Calcular el importe pagado prorrateado para esta línea
                if bill.amount_total > 0:
                    # Proporción pagada de la factura TOTAL
                    # (Total Factura - Pendiente de Pago) / Total Factura
                    paid_ratio = (bill.amount_total - bill.amount_residual) / bill.amount_total

                    # Aplicar esa proporción al 'price_subtotal' de ESTA línea de factura
                    total_paid_amount += bill_line.price_subtotal * paid_ratio

                elif bill.payment_state == 'paid':
                    # Caso borde: Factura con total 0 (ej. nota crédito) pero marcada como pagada
                    total_paid_amount += bill_line.price_subtotal

            line.amount_invoiced = total_invoiced_amount
            line.amount_paid = total_paid_amount

    @api.depends('amount_paid', 'price_subtotal')
    def _compute_purchase_percentage(self):
        """
        Calcula el porcentaje pagado sobre el total de la línea de compra (price_subtotal).
        """
        for line in self:
            if line.price_subtotal > 0:
                # Usamos 'price_subtotal' (total sin impuestos de la línea de PO)
                # como el 100% esperado.
                line.percentage_paid = (line.amount_paid / line.price_subtotal) * 100
            else:
                line.percentage_paid = 0.0


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

    x_sale_total_line_amount_po_currency = fields.Monetary(
        string="Total (Venta)",
        compute='_compute_sale_paid_percentage_total',
        store=True,
        currency_field='currency_id',  # Usamos la moneda de la PO
        help="Suma de todos los importes totales de las líneas de venta asociadas, convertidos a la moneda de esta orden de compra."
    )

    # 2. Campo de ayuda: Suma de los importes pagados de venta (convertidos a la moneda de la PO)
    x_sale_total_paid_amount_po_currency = fields.Monetary(
        string="Total Cobrado (Venta)",
        compute='_compute_sale_paid_percentage_total',
        store=True,
        currency_field='currency_id',  # Usamos la moneda de la PO
        help="Suma de todos los importes cobrados de las líneas de venta asociadas, convertidos a la moneda de esta orden de compra."
    )

    # 3. CAMPO FINAL: El porcentaje total cobrado
    x_sale_paid_percentage_total = fields.Float(
        string="% Cobrado (Venta)",
        compute='_compute_sale_paid_percentage_total',
        store=True,
        digits=(16, 2),
        help="Porcentaje total cobrado de las ventas asociadas, calculado como (Total Cobrado / Total Líneas de Venta)."
    )

    @api.depends('order_line.x_sale_paid_amount',
                 'order_line.x_sale_line_total',
                 'order_line.x_sale_currency_id',
                 'order_line',  # Para recalcular si se añade/quita línea
                 'currency_id',  # Moneda de la PO
                 'date_order')  # Fecha para la tasa de conversión
    def _compute_sale_paid_percentage_total(self):
        """
        Calcula el porcentaje total cobrado de las ventas asociadas
        agregando los importes de las líneas y convirtiendo moneda.
        """
        for po in self:
            total_paid_in_po_currency = 0.0
            total_line_in_po_currency = 0.0

            # Moneda de destino (la de la PO)
            po_currency = po.currency_id

            for line in po.order_line:
                # Moneda de origen (la de la línea de venta)
                sale_currency = line.x_sale_currency_id

                # --- Convertir el importe pagado de la línea de venta ---
                if sale_currency and sale_currency != po_currency:
                    # Usamos _convert para cambiar de la moneda de venta a la moneda de compra
                    total_paid_in_po_currency += sale_currency._convert(
                        line.x_sale_paid_amount,
                        po_currency,
                        po.company_id,
                        po.date_order or fields.Date.today()
                    )
                else:
                    # Las monedas son iguales o no hay moneda de venta
                    total_paid_in_po_currency += line.x_sale_paid_amount

                # --- Convertir el importe total de la línea de venta ---
                if sale_currency and sale_currency != po_currency:
                    total_line_in_po_currency += sale_currency._convert(
                        line.x_sale_line_total,
                        po_currency,
                        po.company_id,
                        po.date_order or fields.Date.today()
                    )
                else:
                    total_line_in_po_currency += line.x_sale_line_total

            # Asignar los valores totales calculados
            po.x_sale_total_paid_amount_po_currency = total_paid_in_po_currency
            po.x_sale_total_line_amount_po_currency = total_line_in_po_currency

            # Calcular el porcentaje final
            if total_line_in_po_currency > 0:
                po.x_sale_paid_percentage_total = (total_paid_in_po_currency / total_line_in_po_currency) * 100
            else:
                po.x_sale_paid_percentage_total = 0.0

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