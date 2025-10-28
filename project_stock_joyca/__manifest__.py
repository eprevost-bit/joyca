# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Project Stock Materials (Project-Picking Link)",
    'summary': """
        Añade un botón en el dashboard del proyecto para ver 
        los materiales (movimientos de stock) asociados.
    """,
    'description': """
                           Este módulo mejora la integración entre los módulos de Proyecto e Inventario.
                           Añade un botón "Materiales Utilizados" en la vista formulario de 'project.project' 
                           que muestra todos los 'stock.move' vinculados al proyecto a través de 'stock.picking'.

                           Funcionalidades:
                           - Añade un campo 'stock_move_count' a 'project.project'.
                           - Añade un botón "Materiales Utilizados" (stat button) al formulario de proyecto.
                           - Define la acción de ventana para mostrar los movimientos de stock ('stock.move').
                       """,
    'author': "Tu Nombre / Tu Compañía",
    'website': "https://www.tuweb.com",
    "version": "18.0.1.0.0",
    'sequence': 0,
    "depends": ['project', 'stock', 'account', 'sale_project', 'sale_timesheet','hr_timesheet'],
    "data": [
        "views/project_views.xml",
        "views/view_account_analytic_line.xml",
    ],

    'assets': {
        'web.assets_backend': [
            'project_stock_joyca/static/src/xml/project_panel.xml',
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
