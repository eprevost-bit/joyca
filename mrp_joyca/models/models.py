from odoo import models, fields

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    state = fields.Selection(
        selection_add=[
            ('medicion', 'Medición'),
            ('sketchup', 'Sketch Up'),
            ('layout', 'Layout'),
            ('fabricacion', 'Fabricación'),
            ('barnizado', 'Barnizado'),
            ('montaje', 'Montaje'),
        ],
        ondelete={
            'medicion': 'set default',
            'sketchup': 'set default',
            'layout': 'set default',
            'fabricacion': 'set default',
            'barnizado': 'set default',
            'montaje': 'set default',
        },
        # Elimina compute y readonly para permitir cambios manuales:
        compute=None,
        readonly=False,
        default='draft',
        tracking=True,  # Opcional: para seguimiento en chatter
    )