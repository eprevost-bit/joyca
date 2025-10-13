# -*- coding: utf-8 -*-

from odoo import models, fields, tools


class ProjectUnifiedLine(models.Model):
    """
    Modelo VIRTUAL para mostrar una vista unificada basada en las líneas de venta
    de un proyecto y sus correspondientes líneas de compra.
    """
    _name = 'project.unified.line'
    _description = 'Línea Unificada de Venta/Compra para Proyectos'
    _auto = False  # Odoo no creará una tabla física para este modelo.

    # --- Campos de la Vista ---
    project_id = fields.Many2one('project.project', string='Proyecto', readonly=True)
    reference = fields.Char(string='Referencia (Venta)', readonly=True)
    line_description = fields.Char(string='Descripción', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)

    # --- Campos de Venta ---
    sale_amount = fields.Monetary(string='Importe venta', readonly=True)
    sale_paid_percentage = fields.Float(string='% Cobrado', readonly=True, group_operator="avg")
    sale_paid_amount = fields.Monetary(string='Importe cobrado', readonly=True)

    # --- Campos de Compra ---
    purchase_amount = fields.Monetary(string='Importe compra', readonly=True)
    purchase_paid_percentage = fields.Float(string='% Pagado', readonly=True, group_operator="avg")
    purchase_paid_amount = fields.Monetary(string='Importe pagado', readonly=True)

    # en models/project_unified_line.py

    # en models/project_unified_line.py

    def _auto_init(self):
        """
        Crea la vista SQL.
        VERSIÓN CORREGIDA: Se corrige el JOIN entre la orden de compra y su factura
        usando el campo 'invoice_origin' que es más robusto entre versiones de Odoo.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH sales_payment_data AS (
                    SELECT
                        so.id AS sale_order_id,
                        SUM(inv.amount_total) AS total_billed,
                        SUM(inv.amount_total - inv.amount_residual) AS total_paid
                    FROM
                        sale_order so
                    JOIN account_move inv ON inv.invoice_origin = so.name
                    WHERE
                        inv.move_type = 'out_invoice' AND inv.state = 'posted'
                    GROUP BY
                        so.id
                ),
                purchase_payment_data AS (
                    SELECT
                        po.id AS purchase_id,
                        SUM(bill.amount_total) AS total_billed,
                        SUM(bill.amount_total - bill.amount_residual) AS total_paid
                    FROM
                        purchase_order po
                    -- *** ¡ESTA ES LA LÍNEA CORREGIDA! ***
                    -- Usamos 'invoice_origin' que coincide con el 'name' de la PO.
                    JOIN account_move bill ON bill.invoice_origin = po.name
                    WHERE
                        bill.move_type = 'in_invoice' AND bill.state = 'posted'
                    GROUP BY
                        po.id
                ),
                main_data AS (
                    SELECT
                        sol.id,
                        sol.order_id,
                        so.project_id,
                        so.name AS reference,
                        sol.name AS line_description,
                        so.currency_id,
                        sol.price_subtotal AS sale_amount,
                        sol.provider_cost AS purchase_amount,
                        po.id as purchase_order_id
                    FROM
                        sale_order_line sol
                    JOIN sale_order so ON (sol.order_id = so.id)
                    LEFT JOIN purchase_order po ON (po.origin = so.name)
                    WHERE
                        so.project_id IS NOT NULL
                    GROUP BY sol.id, so.id, po.id
                )
                -- Ensamblaje Final
                SELECT
                    m.id,
                    m.project_id,
                    m.reference,
                    m.line_description,
                    m.currency_id,
                    m.sale_amount,
                    m.purchase_amount,

                    COALESCE(spd.total_paid, 0) AS sale_paid_amount,
                    CASE
                        WHEN spd.total_billed > 0 THEN (COALESCE(spd.total_paid, 0) / spd.total_billed) * 100
                        ELSE 0
                    END AS sale_paid_percentage,

                    COALESCE(ppd.total_paid, 0) AS purchase_paid_amount,
                    CASE
                        WHEN ppd.total_billed > 0 THEN (COALESCE(ppd.total_paid, 0) / ppd.total_billed) * 100
                        ELSE 0
                    END AS purchase_paid_percentage

                FROM
                    main_data m
                LEFT JOIN sales_payment_data spd ON m.order_id = spd.sale_order_id
                LEFT JOIN purchase_payment_data ppd ON m.purchase_order_id = ppd.purchase_id
            )
        """ % self._table)

    # def _auto_init(self):
    #     """
    #     Crea la vista SQL. La lógica ahora se basa en la relación directa
    #     entre sale.order.line y purchase.order.line.
    #     """
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""
    #         CREATE OR REPLACE VIEW %s AS (
    #             SELECT
    #                 -- El ID de la línea de venta es único y sirve como ID para la vista.
    #                 sol.id AS id,
    #                 so.project_id,
    #                 so.name AS reference,
    #                 sol.name AS line_description,
    #                 so.currency_id,
    #
    #                 -- --- DATOS DE VENTA (Directos de la línea de venta y su pedido) ---
    #                 sol.price_subtotal AS sale_amount,
    #                 -- Los campos de pago vienen del pedido de venta (SO)
    #                 so.percentage_paid AS sale_paid_percentage,
    #                 so.amount_paid AS sale_paid_amount,
    #
    #                 -- --- DATOS DE COMPRA (Agregados desde las líneas de compra vinculadas) ---
    #                 -- Usamos COALESCE para mostrar 0 si no hay línea de compra asociada.
    #                 COALESCE(SUM(pol.price_subtotal), 0) AS purchase_amount,
    #                 -- Los campos de pago vienen del pedido de compra (PO)
    #                 COALESCE(AVG(po.percentage_paid), 0) AS purchase_paid_percentage,
    #                 -- Si múltiples POs están vinculados, sumamos sus pagos.
    #                 COALESCE(SUM(po.amount_paid), 0) AS purchase_paid_amount
    #
    #             FROM
    #                 sale_order_line sol
    #             -- Unimos con el pedido de venta para obtener el proyecto y datos de pago
    #             JOIN sale_order so ON (sol.order_id = so.id)
    #             -- Usamos LEFT JOIN porque una línea de venta puede no tener una compra asociada
    #             LEFT JOIN purchase_order_line pol ON (pol.sale_line_id = sol.id)
    #             LEFT JOIN purchase_order po ON (pol.order_id = po.id)
    #
    #             WHERE
    #                 so.project_id IS NOT NULL
    #
    #             -- Agrupamos por cada línea de venta para consolidar datos de múltiples compras (si existieran)
    #             GROUP BY
    #                 sol.id, so.project_id, so.name, so.currency_id, so.percentage_paid, so.amount_paid
    #         )
    #     """ % self._table)