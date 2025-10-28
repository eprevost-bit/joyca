from odoo import models, fields, api

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    # 1. El nuevo campo "Coste"
    x_coste = fields.Monetary(
        string='Coste',
        compute='_compute_x_coste',
        store=True,  # Importante para poder sumar y agrupar
        readonly=True,
        # Usamos la moneda de la compañía, que es la moneda
        # en la que suele estar el coste del empleado.
        currency_field='currency_id',
        help="Coste calculado: Tiempo dedicado (unit_amount) * Coste/hora del empleado (hourly_cost)"
    )

    @api.depends('unit_amount', 'employee_id.hourly_cost')
    def _compute_x_coste(self):
        """
        Calcula el coste de la línea multiplicando las horas
        por el coste/hora del empleado.
        """
        for line in self:
            # Comprobamos que tengamos un empleado y un coste/hora
            if line.employee_id and line.employee_id.hourly_cost:
                # Esta es la fórmula que pediste:
                line.x_coste = line.unit_amount * line.employee_id.hourly_cost
            else:
                line.x_coste = 0.0