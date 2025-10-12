# -*- coding: utf-8 -*-
# In your custom module: models/project_project.py

from odoo import models, fields, api, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # --- CAMPOS FINANCIEROS CALCULADOS ---
    # Usamos sale_order_id que Odoo crea automáticamente al generar un proyecto desde una venta.

    # Para que el widget 'monetary' funcione correctamente
    currency_id = fields.Many2one(
        'res.currency',
        related='sale_order_id.currency_id',
        string="Moneda"
    )

    # --- Valores de Venta ---
    sale_order_amount_total = fields.Monetary(
        string="Importe Pedido de Venta",
        compute='_compute_financial_summary',
        currency_field='currency_id',
        help="Total del pedido de venta asociado a este proyecto."
    )

    sale_invoice_paid_percent = fields.Float(
        string="% Cobrado (Facturas de Venta)",
        compute='_compute_financial_summary',
        digits=(16, 2),
        help="Porcentaje del total facturado que ha sido cobrado."
    )

    sale_invoice_paid_amount = fields.Monetary(
        string="Importe Cobrado (Facturas de Venta)",
        compute='_compute_financial_summary',
        currency_field='currency_id',
        help="Suma total de los importes cobrados de las facturas de venta asociadas."
    )

    # --- Valores de Compra ---
    purchase_order_amount_total = fields.Monetary(
        string="Importe Pedido de Compra",
        compute='_compute_financial_summary',
        currency_field='currency_id',
        help="Suma total de los pedidos de compra generados desde la venta asociada."
    )

    purchase_bill_paid_percent = fields.Float(
        string="% Pagado (Facturas de Compra)",
        compute='_compute_financial_summary',
        digits=(16, 2),
        help="Porcentaje del total de las facturas de proveedor que ha sido pagado."
    )

    purchase_bill_paid_amount = fields.Monetary(
        string="Importe Pagado (Facturas de Compra)",
        compute='_compute_financial_summary',
        currency_field='currency_id',
        help="Suma total de los importes pagados de las facturas de compra asociadas."
    )

    # In your custom module: models/project_project.py

    @api.depends('sale_order_id',
                 'sale_order_id.invoice_ids.payment_state',
                 'sale_order_id.order_line.qty_invoiced',
                 'task_ids.sale_line_id.order_id')  # <-- Nueva dependencia clave
    def _compute_financial_summary(self):
        """
        Calcula todos los KPIs financieros para el resumen del proyecto.
        Se basa en el pedido de venta original (vínculo directo) Y en los pedidos
        de venta vinculados a través de las tareas del proyecto (vínculo indirecto).
        Suma los valores de todos los pedidos de venta asociados.
        """
        for project in self:
            # --- Inicializamos todos los campos a 0 ---
            project.sale_order_amount_total = 0.0
            project.sale_invoice_paid_percent = 0.0
            project.sale_invoice_paid_amount = 0.0
            project.purchase_order_amount_total = 0.0
            project.purchase_bill_paid_percent = 0.0
            project.purchase_bill_paid_amount = 0.0

            # 1. Recolectar TODOS los pedidos de venta asociados
            all_related_sos = self.env['sale.order']

            # Caso A: Vínculo directo en el proyecto
            if project.sale_order_id:
                all_related_sos |= project.sale_order_id

            # Caso B: Vínculo a través de las tareas del proyecto
            if project.task_ids:
                sos_from_tasks = project.task_ids.mapped('sale_line_id.order_id')
                all_related_sos |= sos_from_tasks

            if not all_related_sos:
                continue

            # --- CÁLCULOS DE VENTA (ahora sobre todos los SOs encontrados) ---
            project.sale_order_amount_total = sum(all_related_sos.mapped('amount_total'))

            customer_invoices = all_related_sos.invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice'
            )

            if customer_invoices:
                total_invoiced = sum(customer_invoices.mapped('amount_total'))
                total_paid = total_invoiced - sum(customer_invoices.mapped('amount_residual'))

                project.sale_invoice_paid_amount = total_paid
                if total_invoiced > 0:
                    project.sale_invoice_paid_percent = (total_paid / total_invoiced) * 100

            # --- CÁLCULOS DE COMPRA (ahora sobre todos los SOs encontrados) ---
            so_names = all_related_sos.mapped('name')
            purchase_orders = self.env['purchase.order'].search([('origin', 'in', so_names)])

            if purchase_orders:
                project.purchase_order_amount_total = sum(purchase_orders.mapped('amount_total'))

                vendor_bills = purchase_orders.invoice_ids.filtered(
                    lambda bill: bill.state == 'posted' and bill.move_type == 'in_invoice'
                )

                if vendor_bills:
                    total_billed = sum(vendor_bills.mapped('amount_total'))
                    total_paid_bills = total_billed - sum(vendor_bills.mapped('amount_residual'))

                    project.purchase_bill_paid_amount = total_paid_bills
                    if total_billed > 0:
                        project.purchase_bill_paid_percent = (total_paid_bills / total_billed) * 100