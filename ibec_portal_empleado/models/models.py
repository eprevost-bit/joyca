from odoo import models, fields

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    archived = fields.Boolean(string="Archivado", default=False)
    auto_generated = fields.Boolean(string="Generado Automáticamente", default=False)