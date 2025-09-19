from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('medicion', 'Medición'),
            ('sketchup', 'Sketch Up'),
            ('layout', 'Layout'),
            ('fabricacion', 'Fabricación'),
            ('barnizado', 'Barnizado'),
            ('montaje', 'Montaje'),
            ('done', 'Finalizado'),
            ('cancel', 'Cancelado')
        ],
        string='Estado',
        default='draft',
        tracking=True,
        copy=False,
        index=True,
        readonly=False,
        store=True,
        help="Estado de la orden de producción"
    )

    # Sobreescribir action_confirm para usar tu primer estado personalizado
    def action_confirm(self):
        for order in self:
            if order.state == 'draft':
                order.state = 'medicion'
        return True

    # Método para avanzar al siguiente estado
    def action_next_state(self):
        state_sequence = [
            'draft',
            'medicion',
            'sketchup',
            'layout',
            'fabricacion',
            'barnizado',
            'montaje',
            'done'
        ]
        for order in self:
            current_index = state_sequence.index(order.state)
            if current_index < len(state_sequence) - 1:
                order.state = state_sequence[current_index + 1]
        return True

    @api.depends('move_raw_ids.state', 'move_raw_ids.quantity', 
                'move_finished_ids.state', 'workorder_ids.state', 
                'product_qty', 'qty_producing', 'move_raw_ids.picked')
    def _compute_state(self):
        """ 
        Computar el estado de producción con los nuevos estados personalizados
        """
        for production in self:
            if not production.state or not production.product_uom_id:
                production.state = 'draft'
            elif production.state == 'cancel':
                production.state = 'cancel'
            elif production.state == 'done':
                production.state = 'done'
            # Lógica adicional para transiciones automáticas si es necesario