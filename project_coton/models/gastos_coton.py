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
    sale_invoiced_percentage = fields.Float(string='% Facturado', readonly=True, group_operator="avg")
    sale_total_invoiced = fields.Monetary(string='Total Facturado Venta', readonly=True)
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
                -- CTEs de facturación (las mantenemos para los importes pagados)
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
                purchase_line_invoice_data AS (
                    SELECT
                        aml.purchase_line_id,
                        SUM(aml.price_total) as total_billed_on_line,
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
                    -- =========================================================================
                    --  AQUÍ ESTÁ EL CAMBIO: Cogemos tu campo y lo multiplicamos por 100
                    --  para que el widget 'progressbar' funcione (espera valores de 0 a 100).
                    -- =========================================================================
                    sol.percentage_invoiced_total * 100 AS sale_invoiced_percentage,
                    sol.amount_paid_line AS sale_paid_amount,
                    COALESCE(sid.total_invoiced, 0) AS sale_total_invoiced,
                    CASE
                        WHEN sid.total_invoiced > 0 THEN (COALESCE(sid.total_paid, 0) / sid.total_invoiced) * 100
                        ELSE 0
                    END AS sale_paid_percentage,

                    -- Campos de Compra (sin cambios)
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
