# -*- coding: utf-8 -*-

from odoo import _,api, fields, models

class ResPartnerLine(models.Model):
    _name = 'res.partner.line'
    _description = 'Línea de Negocio'

    name = fields.Char(string="Nombre de la Línea", required=True)
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'El nombre de la línea debe ser único.')
    ]

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campo nuevo que vincula con el modelo de arriba
    line_id = fields.Many2one(
        'res.partner.line',
        string="Línea de Negocio"
    )