# -*- coding: utf-8 -*-

from odoo import models, fields, tools


class ProjectUnifiedLine(models.Model):
    _name = 'project.unified.line'
    _description = 'Línea Unificada de Venta/Compra para Proyectos (Corregida)'
    _auto = False

    # Los campos del modelo no cambian
    project_id = fields.Many2one('project.project', string='Proyecto', readonly=True)
    reference = fields.Char(string='Referencia (Venta)', readonly=True)
    line_description = fields.Char(string='Descripción', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    quantity = fields.Float(string='Cantidad', readonly=True)
    sale_amount = fields.Monetary(string='Importe Venta (Sin IVA)', readonly=True)
    sale_total_invoiced = fields.Monetary(string='Total Facturado Venta (Con IVA)', readonly=True)
    sale_paid_percentage = fields.Float(string='% Cobrado', readonly=True, group_operator="avg")
    sale_paid_amount = fields.Monetary(string='Importe Cobrado', readonly=True)
    purchase_amount = fields.Monetary(string='Importe Compra (Sin IVA)', readonly=True)
    purchase_total_invoiced = fields.Monetary(string='Total Facturado Compra', readonly=True)
    purchase_paid_percentage = fields.Float(string='% Pagado', readonly=True, group_operator="avg")
    purchase_paid_amount = fields.Monetary(string='Importe Pagado', readonly=True)

    def _auto_init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                -- CTE para facturación de VENTA (por pedido, esto suele ser correcto)
                WITH sales_invoice_data AS (
                    SELECT
                        so.id AS sale_order_id,
                        SUM(inv.amount_total) AS total_invoiced,
                        SUM(inv.amount_total - inv.amount_residual) AS total_paid
                    FROM sale_order so
                    JOIN account_move inv ON inv.invoice_origin = so.name
                    WHERE inv.move_type = 'out_invoice' AND inv.state = 'posted'
                    GROUP BY so.id
                ),
                -- =========================================================================
                --  NUEVA CTE: Calcula importes facturados y pagados POR LÍNEA DE COMPRA
                --  Esto nos da el valor individual que necesitas.
                -- =========================================================================
                purchase_line_invoice_data AS (
                    SELECT
                        aml.purchase_line_id,
                        SUM(aml.price_total) as total_billed_on_line,
                        -- Prorratea el pago de la factura entre sus líneas
                        SUM(
                            CASE
                                WHEN am.amount_total > 0 THEN aml.price_total * ((am.amount_total - am.amount_residual) / am.amount_total)
                                ELSE 0
                            END
                        ) as total_paid_on_line
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    WHERE aml.purchase_line_id IS NOT NULL
                      AND am.move_type = 'in_invoice'
                      AND am.state = 'posted'
                    GROUP BY aml.purchase_line_id
                )
                -- Ensamblaje Final
                SELECT
                    sol.id,
                    so.project_id,
                    so.name AS reference,
                    sol.name AS line_description,
                    sol.product_uom_qty AS quantity,
                    so.currency_id,

                    -- Campos de Venta
                    sol.price_subtotal AS sale_amount,
                    COALESCE(sid.total_invoiced, 0) AS sale_total_invoiced,
                    COALESCE(sid.total_paid, 0) AS sale_paid_amount,
                    CASE
                        WHEN sid.total_invoiced > 0 THEN (COALESCE(sid.total_paid, 0) / sid.total_invoiced) * 100
                        ELSE 0
                    END AS sale_paid_percentage,

                    -- Campos de Compra (usando la nueva CTE con datos por línea)
                    MAX(pol.price_subtotal) AS purchase_amount,
                    MAX(COALESCE(plid.total_billed_on_line, 0)) AS purchase_total_invoiced,
                    MAX(COALESCE(plid.total_paid_on_line, 0)) AS purchase_paid_amount,
                    CASE
                        WHEN MAX(COALESCE(plid.total_billed_on_line, 0)) > 0 THEN
                            (MAX(COALESCE(plid.total_paid_on_line, 0)) / MAX(COALESCE(plid.total_billed_on_line, 0))) * 100
                        ELSE 0
                    END AS purchase_paid_percentage

                FROM
                    sale_order_line sol
                JOIN sale_order so ON sol.order_id = so.id
                LEFT JOIN sales_invoice_data sid ON sid.sale_order_id = so.id

                -- Uniones para llegar a los datos de la línea de compra
                LEFT JOIN purchase_order po ON po.origin = so.name
                LEFT JOIN purchase_order_line pol ON pol.order_id = po.id AND pol.product_id = sol.product_id
                LEFT JOIN purchase_line_invoice_data plid ON plid.purchase_line_id = pol.id

                WHERE
                    so.project_id IS NOT NULL

                GROUP BY
                    sol.id,
                    so.project_id,
                    so.name,
                    so.currency_id,
                    sid.total_invoiced,
                    sid.total_paid
            )
        """ % self._table)
    # def _auto_init(self):
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""
    #         CREATE OR REPLACE VIEW %s AS (
    #             -- CTE para agrupar datos de facturación de VENTA por pedido
    #             WITH sales_invoice_data AS (
    #                 SELECT
    #                     so.id AS sale_order_id,
    #                     SUM(inv.amount_total) AS total_invoiced,
    #                     SUM(inv.amount_total - inv.amount_residual) AS total_paid
    #                 FROM sale_order so
    #                 JOIN account_move inv ON inv.invoice_origin = so.name
    #                 WHERE inv.move_type = 'out_invoice' AND inv.state = 'posted'
    #                 GROUP BY so.id
    #             ),
    #             -- CTE para agrupar datos de facturación de COMPRA por pedido
    #             purchase_invoice_data AS (
    #                 SELECT
    #                     po.id AS purchase_id,
    #                     SUM(bill.amount_total) AS total_billed,
    #                     SUM(bill.amount_total - bill.amount_residual) AS total_paid
    #                 FROM purchase_order po
    #                 JOIN account_move bill ON bill.invoice_origin = po.name
    #                 WHERE bill.move_type = 'in_invoice' AND bill.state = 'posted'
    #                 GROUP BY po.id
    #             )
    #             -- Ensamblaje Final
    #             SELECT
    #                 sol.id,
    #                 so.project_id,
    #                 so.name AS reference,
    #                 sol.name AS line_description,
    #                 sol.product_uom_qty AS quantity,
    #                 so.currency_id,
    #
    #                 -- Campos de Venta (directos de la línea de venta y su CTE)
    #                 sol.price_subtotal AS sale_amount,
    #                 COALESCE(sid.total_invoiced, 0) AS sale_total_invoiced,
    #                 COALESCE(sid.total_paid, 0) AS sale_paid_amount,
    #                 CASE
    #                     WHEN sid.total_invoiced > 0 THEN (COALESCE(sid.total_paid, 0) / sid.total_invoiced) * 100
    #                     ELSE 0
    #                 END AS sale_paid_percentage,
    #
    #                 -- Campos de Compra (Agregados aquí para evitar duplicados)
    #                 MAX(pol.price_subtotal) AS purchase_amount,-- Se suma el subtotal de las líneas de compra vinculadas
    #                 MAX(COALESCE(pid.total_billed, 0)) AS purchase_total_invoiced, -- MAX para no sumar el total de la factura varias veces
    #                 MAX(COALESCE(pid.total_paid, 0)) AS purchase_paid_amount, -- MAX para no sumar el pago varias veces
    #                 CASE
    #                     WHEN MAX(COALESCE(pid.total_billed, 0)) > 0 THEN (MAX(COALESCE(pid.total_paid, 0)) / MAX(COALESCE(pid.total_billed, 0))) * 100
    #                     ELSE 0
    #                 END AS purchase_paid_percentage
    #
    #             FROM
    #                 sale_order_line sol
    #             JOIN sale_order so ON sol.order_id = so.id
    #             LEFT JOIN sales_invoice_data sid ON sid.sale_order_id = so.id
    #
    #             -- Se unen las compras aquí directamente
    #             LEFT JOIN purchase_order po ON po.origin = so.name
    #             -- La unión clave: de la línea de venta a la de compra a través del producto
    #             LEFT JOIN purchase_order_line pol ON pol.order_id = po.id AND pol.product_id = sol.product_id
    #             LEFT JOIN purchase_invoice_data pid ON pid.purchase_id = po.id
    #
    #             WHERE
    #                 so.project_id IS NOT NULL
    #
    #             -- El GROUP BY correcto: Agrupamos por cada línea de venta y sus datos relacionados
    #             GROUP BY
    #                 sol.id,
    #                 so.project_id,
    #                 so.name,
    #                 sol.name,
    #                 so.currency_id,
    #                 sid.total_invoiced,
    #                 sid.total_paid
    #         )
    #     """ % self._table)