# -*- coding: utf-8 -*-

from odoo import models, fields, tools


class ProjectUnifiedLine(models.Model):
    _name = 'project.unified.line'
    _description = 'Línea Unificada de Venta/Compra para Proyectos (Corregida)'
    _auto = False

    # Los campos del modelo no cambian
    project_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        required=True,
        ondelete='cascade',
        index=True
    )
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
                -- =========================================================================
                --  El CTE se mantiene igual porque todavía se necesita para calcular
                --  los totales de compra facturados y pagados.
                -- =========================================================================
                WITH
                aggregated_purchase_data AS (
                    SELECT
                        po.origin,
                        pol.product_id,
                        SUM(pol.price_subtotal) AS total_purchase_amount,
                        SUM(pol.price_subtotal * pol.percentage_invoiced) AS total_purchase_invoiced,
                        SUM(pol.amount_paid_line) AS total_purchase_paid
                    FROM purchase_order_line pol
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE po.origin IS NOT NULL AND pol.display_type IS NULL
                    GROUP BY po.origin, pol.product_id
                )
                -- 2. Ensamblaje Final
                SELECT
                    sol.id,
                    so.project_id,
                    so.name AS reference,
                    sol.name AS line_description,
                    sol.product_uom_qty AS quantity,
                    so.currency_id,

                    -- CAMPOS DE VENTA (Sin cambios)
                    sol.price_subtotal AS sale_amount,
                    (sol.percentage_invoiced_total * 100) AS sale_invoiced_percentage,
                    (sol.price_subtotal * sol.percentage_invoiced_total) AS sale_total_invoiced,
                    sol.amount_paid_line AS sale_paid_amount,
                    CASE
                        WHEN (sol.price_subtotal * sol.percentage_invoiced_total) > 0 THEN
                            (sol.amount_paid_line / (sol.price_subtotal * sol.percentage_invoiced_total)) * 100
                        ELSE 0
                    END AS sale_paid_percentage,

                    -- ======================================================================
                    -- >> ÚNICO CAMBIO REALIZADO AQUÍ <<
                    -- Se calcula 'purchase_amount' usando el campo 'provider_cost' de la
                    -- línea de venta (sol) multiplicado por la cantidad.
                    -- ======================================================================
                    (COALESCE(sol.provider_cost, 0) * sol.product_uom_qty) AS purchase_amount,

                    -- El resto de campos de compra siguen usando el CTE como antes
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
                -- El JOIN se mantiene para los otros cálculos de compra
                LEFT JOIN aggregated_purchase_data apd ON apd.origin = so.name AND apd.product_id = sol.product_id

                WHERE
                    so.project_id IS NOT NULL
                    AND sol.display_type IS NULL
            )
        """ % self._table)