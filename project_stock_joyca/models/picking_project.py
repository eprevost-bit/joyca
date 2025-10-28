# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class Project(models.Model):
    _inherit = "project.project"

    # --- CAMPO CALCULADO ---

    stock_move_count = fields.Integer(
        string='Materiales Utilizados',
        compute='_compute_stock_move_count'
    )

    def _compute_stock_move_count(self):
        """
        Calcula el número de movimientos de stock asociados al proyecto.
        """
        for project in self:
            project.stock_move_count = self.env['stock.move'].search_count([
                ('picking_id.project_id', '=', project.id)
            ])

    # --- PASO 1: AÑADIR LOS METADATOS DEL BOTÓN ---

    def _get_stat_buttons(self):
        """
        Hereda los botones de estadísticas del dashboard OWL
        para añadir el nuestro, usando el patrón correcto de Odoo 18.
        """
        buttons = super(Project, self)._get_stat_buttons()

        buttons.append({
            'icon': 'credit-card',
            'text': _('Materiales Utilizados'),
            'number': self.stock_move_count,
            'action_type': 'object',
            'action': 'action_view_project_stock_moves',
            'show': self.stock_move_count > 0,
            'sequence': 10,
        })

        return buttons

    # --- PASO 2: INYECTAR LA DEFINICIÓN DE LA ACCIÓN ---

    def _get_project_dashboard_data(self):

        # Obtiene todos los datos originales (incluyendo nuestros botones)
        data = super(Project, self)._get_project_dashboard_data()

        # Aseguramos que el dict 'actions' exista
        if 'actions' not in data:
            data['actions'] = {}

        # Añadimos la definición de nuestra acción
        # La clave 'stock_moves_action' DEBE COINCIDIR con el 'name'
        # del botón en _get_stat_buttons.
        action = self.env.ref('project_stock_joyca.action_project_stock_moves')
        if action:
            data['actions']['stock_moves_action'] = action.read(load=False)[0]

        return data

    def action_view_project_stock_moves(self):
        """
        Esta función abre la vista de movimientos de stock.
        """
        return {
            'name': _('Materiales Utilizados'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('picking_id.project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def _get_profitability_labels(self):

        labels = super()._get_profitability_labels()

        # Cambiamos 'A facturar' por 'Total'
        # Es importante mantener el nombre de la clave original ('to_invoice')
        if 'to_invoice' in labels:
            labels['to_invoice'] = _('Total')

        return labels

    def _get_panel_sale_orders(self):
        """
        Busca y formatea los PEDIDOS de venta (agrupados) para el panel.
        """
        self.ensure_one()

        # Buscamos los Pedidos de Venta vinculados a este proyecto
        sale_orders = self.env['sale.order'].search([
            ('project_id', '=', self.id),
            ('state', 'in', ['sale', 'done']),
        ])

        so_data = []
        for order in sale_orders:
            # 1. Total del pedido (usamos el subtotal sin impuestos)
            total_amount = order.amount_untaxed

            # 2. Calcular el importe total facturado (sin impuestos)
            invoiced_amount = 0.0

            # Filtramos facturas publicadas (posted)
            posted_invoices = order.invoice_ids.filtered(
                lambda m: m.state == 'posted'
            )
            for inv in posted_invoices:
                # amount_untaxed_signed maneja correctamente facturas y abonos
                invoiced_amount += inv.amount_untaxed_signed

            so_data.append({
                'id': order.id,
                'sale_order_name': order.name,
                'total_amount': total_amount,
                'invoiced_amount': invoiced_amount,
                'currency_id': order.currency_id.id,
                'date_order': order.date_order,
            })
        return so_data

    def _get_panel_timesheet_totals(self):
        """
        Calcula los totales de horas y coste para el panel.
        """
        self.ensure_one()
        timesheets = self.env['account.analytic.line'].search([
            ('project_id', '=', self.id),
            ('employee_id', '!=', False),
        ])

        total_hours = 0.0
        total_cost = 0.0
        # Usaremos la moneda del proyecto como moneda de destino
        project_currency = self.currency_id

        for line in timesheets:
            # Sumar las horas
            total_hours += line.unit_amount

            # Sumar el coste, convirtiendo la moneda si es necesario
            line_cost = line.x_coste
            if line.currency_id and line.currency_id != project_currency:
                # Convertir el coste de la línea a la moneda del proyecto
                total_cost += line.currency_id._convert(
                    line_cost,
                    project_currency,
                    self.company_id or self.env.company,
                    line.date or fields.Date.today()
                )
            else:
                # La moneda es la misma (o no hay moneda), sumar directamente
                total_cost += line_cost

        # Devolvemos un solo diccionario con los totales
        return {
            'total_hours': total_hours,
            'total_cost': total_cost,
            'currency_id': project_currency.id,
        }

    def _get_panel_stock_moves(self):
        """
        Busca y formatea los movimientos de stock (materiales) para el panel.
        """
        self.ensure_one()
        stock_moves = self.env['stock.move'].search([
            ('picking_id.project_id', '=', self.id),
            ('state', '=', 'done')
        ])

        move_data = []
        for move in stock_moves:
            move_data.append({
                'id': move.id,
                'product_name': move.product_id.display_name,

                # --- CORREGIDO ---
                'quantity_done': move.product_uom_qty,  # Usamos la cantidad hecha
                # --- FIN CORRECCIÓN ---

                'product_uom': move.product_uom.name,

                # --- CORREGIDO ---
                'cost': move.x_coste_total,  # Sin la 'e' extra
                # --- FIN CORRECCIÓN ---

                'currency_id': move.currency_id.id,
                'date': move.date,
            })
        return move_data

    def get_panel_data(self):
        """
        Heredamos la función principal para inyectar todos los datos
        Y AÑADIMOS EL CÁLCULO DEL MARGEN.
        """
        panel_data = super().get_panel_data()

        if self.env.user.has_group('project.group_project_user'):

            project_currency = self.currency_id
            company = self.company_id or self.env.company
            today = fields.Date.today()  # Fecha de fallback

            # 1. INGRESOS (Ventas)
            panel_sale_orders = self._get_panel_sale_orders()
            panel_data['panel_sale_orders'] = panel_sale_orders

            total_revenue = 0.0
            for order in panel_sale_orders:
                order_currency = self.env['res.currency'].browse(order['currency_id'])
                total_revenue += order_currency._convert(
                    order['total_amount'],
                    project_currency,
                    company,
                    order.get('date_order', today)
                )

            # 2. COSTE (Horas)
            panel_timesheet_totals = self._get_panel_timesheet_totals()
            panel_data['panel_timesheet_totals'] = panel_timesheet_totals
            # Este coste ya está en la moneda del proyecto (según nuestra función)
            total_hours_cost = panel_timesheet_totals['total_cost']

            # 3. COSTE (Materiales)
            panel_stock_moves = self._get_panel_stock_moves()
            panel_data['panel_stock_moves'] = panel_stock_moves

            total_material_cost = 0.0
            for move in panel_stock_moves:
                move_currency = self.env['res.currency'].browse(move['currency_id'])
                total_material_cost += move_currency._convert(
                    move['cost'],
                    project_currency,
                    company,
                    move.get('date', today)
                )

            # 4. CÁLCULO DEL MARGEN
            margin_amount = total_revenue - total_hours_cost - total_material_cost
            margin_percentage = (total_revenue and (margin_amount / total_revenue) * 100) or 0.0

            # 5. Guardar datos del margen para el XML
            panel_data['panel_margin'] = {
                'total_revenue': total_revenue,
                'total_hours_cost': total_hours_cost,
                'total_material_cost': total_material_cost,
                'margin_amount': margin_amount,
                'margin_percentage': margin_percentage,
                'currency_id': project_currency.id,
            }

            if 'currency_id' not in panel_data:
                panel_data['currency_id'] = project_currency.id

        return panel_data

    # def get_panel_data(self):
    #     """
    #     Heredamos la función principal para inyectar nuestros nuevos datos.
    #     """
    #     panel_data = super().get_panel_data()
    #
    #     if self.env.user.has_group('project.group_project_user'):
    #
    #         panel_data['panel_sale_orders'] = self._get_panel_sale_orders()
    #
    #         # --- LÍNEA CORREGIDA ---
    #         # La clave ahora es 'panel_timesheet_totals'
    #         panel_data['panel_timesheet_totals'] = self._get_panel_timesheet_totals()
    #         # --- FIN DE LA CORRECCIÓN ---
    #
    #         panel_data['panel_stock_moves'] = self._get_panel_stock_moves()
    #
    #         if 'currency_id' not in panel_data:
    #             panel_data['currency_id'] = self.currency_id.id
    #
    #     return panel_data

