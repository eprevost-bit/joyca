# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    # --- CAMPOS ORIGINALES (Puedes mantenerlos si los necesitas en otro lugar) ---
    sale_order_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='project_id',
        string='Órdenes de Venta'
    )
    purchase_order_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='project_id',
        string='Órdenes de Compra'
    )

    unified_line_ids = fields.One2many(
        comodel_name='project.unified.line',
        inverse_name='project_id',
        string='Líneas de Venta y Compra',
        readonly=True
    )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    amount_paid_line = fields.Monetary(
        string = "Importe Cobrado",
        compute='_compute_amount_paid_line',
        store=True,
        readonly=True,
        help="Cantidad total que ha sido pagada por el cliente para esta línea específica, "
             "calculada proporcionalmente a los pagos de las facturas asociadas."
    )

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.move_id.amount_residual_signed')
    def _compute_amount_paid_line(self):
        """
        Calcula el importe pagado SIN IVA para una línea de pedido de venta específica.

        Itera sobre todas las líneas de factura asociadas a esta línea de venta.
        Para cada factura, calcula qué porcentaje ha sido pagado y aplica ese
        porcentaje al valor SIN IVA de la línea de factura correspondiente.
        """
        for line in self:
            total_paid_on_line = 0.0

            # Recorremos todas las líneas de factura que se crearon desde esta línea de venta
            for invoice_line in line.invoice_lines:
                invoice = invoice_line.move_id

                # Solo consideramos facturas confirmadas ('posted')
                if invoice.state != 'posted':
                    continue

                # La proporción de pago de la factura se calcula sobre los totales (con IVA)
                # Esta lógica es correcta y no necesita cambios.
                payment_ratio = 0.0
                # Usamos amount_total_signed para manejar correctamente notas de crédito
                if invoice.amount_total_signed != 0:
                    amount_paid_on_invoice = invoice.amount_total_signed - invoice.amount_residual_signed
                    payment_ratio = amount_paid_on_invoice / invoice.amount_total_signed

                # =========================================================================
                # ¡CAMBIO CLAVE AQUÍ!
                # Aplicamos esa proporción al valor de la línea de factura SIN IMPUESTOS.
                #   - invoice_line.price_total -> Importe con IVA
                #   - invoice_line.price_subtotal -> Importe SIN IVA
                # =========================================================================
                total_paid_on_line += invoice_line.price_subtotal * payment_ratio

            line.amount_paid_line = total_paid_on_line


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # ¡NUEVO CAMPO PARA COMPRAS!
    amount_paid_line = fields.Monetary(
        string="Importe Pagado",
        compute='_compute_amount_paid_line',
        store=True,
        readonly=True,
        help="Cantidad total (sin IVA) que ha sido pagada al proveedor por esta línea específica, "
             "calculada proporcionalmente a los pagos de las facturas asociadas."
    )

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.move_id.amount_residual_signed')
    def _compute_amount_paid_line(self):
        """
        Calcula el importe pagado SIN IVA para una línea de pedido de compra específica.

        Itera sobre todas las líneas de factura de proveedor asociadas. Para cada factura,
        calcula qué porcentaje ha sido pagado y aplica ese porcentaje al valor
        SIN IVA de la línea de factura correspondiente.
        """
        for line in self:
            total_paid_on_line = 0.0

            # Recorremos todas las líneas de factura de proveedor creadas desde esta línea de compra
            for invoice_line in line.invoice_lines:
                bill = invoice_line.move_id  # 'bill' es más claro para facturas de proveedor

                # Solo consideramos facturas confirmadas ('posted')
                # y que sean del tipo correcto (facturas de proveedor)
                if bill.state != 'posted' or not bill.move_type.startswith('in_'):
                    continue

                # Calculamos la proporción de pago de la factura
                payment_ratio = 0.0
                if bill.amount_total_signed != 0:
                    amount_paid_on_bill = bill.amount_total_signed - bill.amount_residual_signed
                    payment_ratio = amount_paid_on_bill / bill.amount_total_signed

                # Aplicamos esa proporción al valor de la línea de factura SIN IMPUESTOS
                # La lógica es idéntica a la de ventas: usamos price_subtotal
                total_paid_on_line += invoice_line.price_subtotal * payment_ratio

            line.amount_paid_line = total_paid_on_line