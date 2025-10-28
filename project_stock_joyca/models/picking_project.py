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

    def _get_panel_sale_order_lines(self):
        """
        Busca y formatea las líneas de pedido de venta para el panel.
        ¡CORREGIDO! Ahora busca por el campo project_id en sale.order.
        """
        self.ensure_one()

        # Buscamos líneas de pedidos de venta vinculados a este proyecto
        sale_lines = self.env['sale.order.line'].search([
            ('order_id.project_id', '=', self.id), # <- ESTA ES LA LÍNEA CORREGIDA
            ('order_id.state', 'in', ['sale', 'done']),
            ('display_type', '=', False), # Excluimos secciones, notas, etc.
        ])

        sol_data = []
        for line in sale_lines:
            # Calcular el importe facturado para esta línea
            invoiced_amount = 0.0
            for inv_line in line.invoice_lines:
                if inv_line.move_id.state == 'posted':
                    if inv_line.move_id.move_type == 'out_invoice':
                        invoiced_amount += inv_line.price_subtotal
                    elif inv_line.move_id.move_type == 'out_refund':
                        invoiced_amount -= inv_line.price_subtotal

            sol_data.append({
                'id': line.id,
                'sale_order_name': line.order_id.name,
                'line_description': line.name,
                # Usamos price_total (con impuestos) o price_subtotal (sin impuestos)
                # según tu necesidad. "Importe total" suele ser price_total.
                'total_amount': line.price_total,
                'invoiced_amount': invoiced_amount,
                'currency_id': line.currency_id.id,
            })
        return sol_data

    def _get_panel_timesheet_lines(self):

        self.ensure_one()
        timesheets = self.env['account.analytic.line'].search([
            ('project_id', '=', self.id),
            ('employee_id', '!=', False),  # Solo líneas con empleado
        ])

        ts_data = []
        for line in timesheets:
            # El campo 'amount' en AAL para partes de horas suele ser el coste (negativo).
            # Usamos abs() para mostrarlo como un coste positivo.
            cost = abs(line.amount)

            ts_data.append({
                'id': line.id,
                'display_name': f"{line.employee_id.name or _('N/A')}: {line.name}",
                'hours': line.unit_amount,
                'amount': cost,
                # Usamos la moneda de la propia línea analítica, es lo más seguro
                'currency_id': line.currency_id.id,
            })
        return ts_data

    def get_panel_data(self):
        """
        Heredamos la función principal para inyectar nuestros nuevos datos.
        """
        # Obtenemos todos los datos estándar llamando a 'super'
        panel_data = super().get_panel_data()

        # Solo añadimos los datos si el usuario tiene permisos
        if self.env.user.has_group('project.group_project_user'):
            # Añadimos nuestras nuevas listas de datos
            panel_data['panel_sale_lines'] = self._get_panel_sale_order_lines()
            panel_data['panel_timesheet_lines'] = self._get_panel_timesheet_lines()

            # Aseguramos que la moneda principal esté disponible para formatear
            if 'currency_id' not in panel_data:
                panel_data['currency_id'] = self.currency_id.id

        return panel_data