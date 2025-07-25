from odoo import api, fields, models
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_section_untaxed_amount = fields.Monetary(
        string="Total de la Sección (Base Imponible)",
        compute='_compute_section_untaxed_amount',
        store=True,
        currency_field='currency_id'
    )
    product_default_code = fields.Char(
        related='product_id.default_code',
        string="Referencia Interna del Producto",
        store=True
    )

    @api.depends('order_id.order_line', 'order_id.order_line.price_subtotal', 'display_type', 'sequence')
    def _compute_section_untaxed_amount(self):
        """
        Calcula el subtotal para cada sección.
        Una sección empieza con una línea 'line_section' y termina justo antes de la siguiente 'line_section'.
        """
        # Agrupamos por pedido para procesar cada uno por separado
        for order in self.mapped('order_id'):
            subtotal_cache = {}
            # Ordenamos las líneas por secuencia para asegurar el orden correcto
            lines = order.order_line.sorted('sequence')
            
            # Buscamos los índices de las líneas que son secciones
            section_indices = [i for i, line in enumerate(lines) if line.display_type == 'line_section']
            
            for i, section_start_index in enumerate(section_indices):
                section_line = lines[section_start_index]
                
                # Determinamos el final del rango de la sección actual
                if i + 1 < len(section_indices):
                    section_end_index = section_indices[i + 1]
                else:
                    section_end_index = len(lines)
                
                section_total = sum(
                    l.price_subtotal for l in lines[section_start_index + 1:section_end_index] if not l.display_type
                )
                subtotal_cache[section_line.id] = section_total
            
            for line in self:
                if line.order_id == order:
                    if line.display_type == 'line_section':
                        line.x_section_untaxed_amount = subtotal_cache.get(line.id, 0)
                    else:
                        line.x_section_untaxed_amount = 0

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    conecpt_sale = fields.Char(string="Conecpto de Venta")
    project_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        ondelete='set null',
        index=True,
        copy=False,
    )
    cantidad = fields.Float(
            string='Cantidad',
            digits=(16, 6)  
        )
    
    @api.onchange('order_line')
    def _onchange_recalculate_percentages(self):
        """
        Calcula el precio de las líneas de porcentaje basado en el 
        subtotal de las líneas de producto normales.
        """
        # 1. Separar las líneas normales de las de porcentaje
        percentage_lines = self.order_line.filtered(
            lambda line: line.product_id and line.product_id.x_percentage_of_total > 0
        )
        
        normal_lines = self.order_line - percentage_lines

        # 2. Calcular el subtotal base (solo de las líneas normales)
        base_subtotal = sum(normal_lines.mapped('price_subtotal'))

        # 3. Actualizar el precio de cada línea de porcentaje
        for line in percentage_lines:
            percentage = line.product_id.x_percentage_of_total / 100.0
            line.price_unit = base_subtotal * percentage
            line.product_uom_qty = 1 

    def action_add_custom_section(self):
        self.ensure_one()
        service_refs = [
            'SERV-CAJONES', 'SERV-PLATAFORMA', 'SERV-DESPLAZAMIENTO', 
            'SERV-REPARTO', 'SERV-FABRICACION', 'SERV-MONTAJE'
        ]
        percentage_refs = ['PCT-MUESTRA', 'PCT-BARNIZ', 'PCT-OFITEC', 'PCT-REPASOS']
        all_refs = service_refs + percentage_refs
        
        products = self.env['product.product'].search([('default_code', 'in', all_refs)])
        products_by_ref = {p.default_code: p for p in products}
        
        missing_refs = [ref for ref in all_refs if ref not in products_by_ref]
        if missing_refs:
            raise UserError(f"No se encontraron los siguientes productos necesarios: {', '.join(missing_refs)}. "
                            "Por favor, créalos o asegúrate de que su 'Referencia Interna' sea correcta.")

        sequence = max(self.order_line.mapped('sequence') or [0]) + 1
        lines_to_create = []

        lines_to_create.append((0, 0, {
            'display_type': 'line_section',
            'name': 'SERVICIOS ADICIONALES',
            'sequence': sequence
        }))
        sequence += 1

        for ref in service_refs:
            product = products_by_ref[ref]
            lines_to_create.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': 0,
                'price_unit': product.list_price,
                'sequence': sequence
            }))
            sequence += 1
            
        lines_to_create.append((0, 0, {
            'display_type': 'line_note',
            'name': 'Cargos por porcentaje sobre la sección',
            'sequence': sequence
        }))
        sequence += 1

        for ref in percentage_refs:
            product = products_by_ref[ref]
            lines_to_create.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': 0,
                'sequence': sequence
            }))
            sequence += 1
            
        self.write({
            'order_line': lines_to_create
        })
        self._recalculate_percentage_lines()
        
        return True

    @api.onchange('order_line')
    def _recalculate_percentage_lines(self):
        
        sections = {}
        current_section_id = None
        for line in self.order_line:
            if line.display_type == 'line_section':
                current_section_id = line.id
                sections[current_section_id] = {'subtotal': 0.0, 'percentage_lines': []}
                continue 

            if not current_section_id:
                continue

            if line.product_id.default_code and line.product_id.default_code.startswith('PCT-'):
                sections[current_section_id]['percentage_lines'].append(line)
            elif line.display_type is False:
                sections[current_section_id]['subtotal'] += line.price_subtotal

        for section_id, data in sections.items():
            section_subtotal = data['subtotal']
            for perc_line in data['percentage_lines']:
                percentage = perc_line.product_id.product_tmpl_id.x_section_percentage or 0.0
                perc_line.price_unit = section_subtotal * percentage
                perc_line.product_uom_qty = 1
            