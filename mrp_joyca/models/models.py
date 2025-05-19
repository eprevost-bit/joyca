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

    @api.depends('move_raw_ids.state', 'move_raw_ids.quantity', 
                'move_finished_ids.state', 'workorder_ids.state', 
                'product_qty', 'qty_producing', 'move_raw_ids.picked')
    def _compute_state(self):
        """ 
        Computar el estado de producción con los nuevos estados personalizados
        """
        for production in self:
            # Mantener la lógica básica pero adaptada a tus estados
            if not production.state or not production.product_uom_id:
                production.state = 'draft'
            elif production.state == 'cancel':
                production.state = 'cancel'
            elif production.state == 'done':
                production.state = 'done'
            # Aquí puedes añadir más lógica para tus estados personalizados
            # Por ejemplo:
            elif production.state == 'fabricacion' and all(move.state == 'done' for move in production.move_raw_ids):
                production.state = 'montaje'