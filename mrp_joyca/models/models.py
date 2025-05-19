from odoo import models, fields

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Redefinir el campo 'state' con los nuevos estados
    state = fields.Selection(
        selection_add=[
            ('draft', 'Borrador'),
            ('medicion', 'Medición'),
            ('sketchup', 'Sketch Up'),
            ('layout', 'Layout'),
            ('fabricacion', 'Fabricación'),
            ('barnizado', 'Barnizado'),
            ('montaje', 'Montaje'),
            ('done', 'Finalizado'),
        ],
        default='draft',
        ondelete={
            'draft': 'set default',
            'medicion': 'set default',
            'sketchup': 'set default',
            'layout': 'set default',
            'fabricacion': 'set default',
            'barnizado': 'set default',
            'montaje': 'set default',
        }
    )