# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectProject(models.Model):
    # Heredamos del modelo de proyecto para añadir nuestro campo
    _inherit = 'project.project'

    # Creamos el campo para almacenar el código del proyecto.
    # readonly=True: El usuario no puede editarlo manualmente desde la vista.
    # copy=False: Al duplicar un proyecto, este campo no se copia, forzando la generación de un nuevo código.
    # index=True: Es buena práctica para mejorar la velocidad de búsqueda sobre este campo.
    project_code = fields.Char(
        string='Código de Proyecto',
        readonly=True,
        copy=False,
        index=True
    )

    # Añadimos una restricción a nivel de base de datos para asegurar que no haya dos
    # proyectos con el mismo código. Es una capa extra de seguridad.
    _sql_constraints = [
        ('project_code_unique', 'unique(project_code)', '¡El código del proyecto debe ser único!')
    ]