from odoo import models, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model
    def create(self, vals):
        name = (vals.get('name') or '').strip()

        sequence = self.env['ir.sequence'].next_by_code(
            'project.project'
        )

        if sequence:
            if name:
                vals['name'] = f"{sequence} {name}"
            else:
                vals['name'] = sequence

        return super().create(vals)
