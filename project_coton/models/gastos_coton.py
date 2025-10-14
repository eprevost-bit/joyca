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
                WITH
                -- 1. Primero, calculamos los totales facturados y pagados por cada línea de compra.
                -- Esto evita duplicar montos si una línea de compra tiene varias facturas.
                purchase_invoice_summary AS (
                    SELECT
                        aml.purchase_line_id,
                        SUM(aml.price_subtotal) AS total_invoiced,
                        SUM(
                            CASE
                                WHEN am.amount_total != 0 THEN aml.price_subtotal * (1 - (am.amount_residual / am.amount_total))
                                ELSE 0
                            END
                        ) AS total_paid
                    FROM account_move_line aml
                    JOIN account_move am ON aml.move_id = am.id
                    WHERE aml.purchase_line_id IS NOT NULL
                      AND am.move_type = 'in_invoice'
                      AND am.state = 'posted'
                    GROUP BY aml.purchase_line_id
                ),
                -- 2. Ahora, agregamos todos los datos de compra (coste original, facturado y pagado)
                -- por Pedido de Venta de Origen (po.origin) y por producto.
                aggregated_purchase_data AS (
                    SELECT
                        po.origin,
                        pol.product_id,
                        SUM(pol.price_subtotal) AS total_purchase_amount,
                        SUM(COALESCE(pis.total_invoiced, 0)) AS total_purchase_invoiced,
                        SUM(COALESCE(pis.total_paid, 0)) AS total_purchase_paid
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    LEFT JOIN purchase_invoice_summary pis ON pol.id = pis.purchase_line_id
                    WHERE po.origin IS NOT NULL
                    GROUP BY po.origin, pol.product_id
                )
                -- 3. Ensamblaje Final: Unimos las líneas de venta con los datos de compra agregados.
                SELECT
                    sol.id,
                    so.project_id,
                    so.name AS reference,
                    sol.name AS line_description,
                    sol.currency_id,
                    sol.product_uom_qty AS quantity,

                    -- CAMPOS DE VENTA (Como los tenías)
                    sol.price_subtotal AS sale_amount,
                    COALESCE(sol.percentage_invoiced_total * 100, 0) AS sale_invoiced_percentage,
                    COALESCE(sol.price_subtotal * sol.percentage_invoiced_total, 0) AS sale_total_invoiced,
                    COALESCE(sol.amount_paid_line, 0) AS sale_paid_amount,
                    CASE
                        WHEN (sol.price_subtotal * sol.percentage_invoiced_total) > 0 THEN
                            (sol.amount_paid_line / (sol.price_subtotal * sol.percentage_invoiced_total)) * 100
                        ELSE 0
                    END AS sale_paid_percentage,

                    -- CAMPOS DE COMPRA (Usando los datos de nuestro CTE 'aggregated_purchase_data')
                    COALESCE(apd.total_purchase_amount, 0) AS purchase_amount,
                    COALESCE(apd.total_purchase_invoiced, 0) AS purchase_total_invoiced,
                    COALESCE(apd.total_purchase_paid, 0) AS purchase_paid_amount,
                    CASE
                        WHEN apd.total_purchase_invoiced > 0 THEN
                            (apd.total_purchase_paid / apd.total_purchase_invoiced) * 100
                        ELSE 0
                    END AS purchase_paid_percentage

                FROM
                    sale_order_line sol
                JOIN sale_order so ON sol.order_id = so.id
                LEFT JOIN aggregated_purchase_data apd ON apd.origin = so.name AND apd.product_id = sol.product_id

                WHERE
                    so.project_id IS NOT NULL
                    AND sol.display_type IS NULL
            )
        """ % self._table)