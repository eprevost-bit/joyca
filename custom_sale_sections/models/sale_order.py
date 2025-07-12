# custom_sale_sections/models/sale_order.py
from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('order_line')
    def _recalculate_percentage_lines(self):
        sections = {}
        current_section_id = None
        for line in self.order_line:
            if line.display_type == 'line_section':
                current_section_id = line.id
                sections[current_section_id] = {'subtotal': 0.0, 'percentage_lines': []}
            elif current_section_id:
                if line.product_id.default_code and line.product_id.default_code.startswith('PCT-'):
                    sections[current_section_id]['percentage_lines'].append(line)
                elif line.display_type not in ['line_note']:
                    sections[current_section_id]['subtotal'] += line.price_subtotal

        for section_id, data in sections.items():
            section_subtotal = data['subtotal']
            for perc_line in data['percentage_lines']:
                percentage = perc_line.product_id.x_section_percentage or 0.0
                perc_line.price_unit = section_subtotal * percentage
                
                # --- CORRECCIÓN CLAVE AQUÍ ---
                # El campo correcto para la cantidad es 'product_uom_qty', no 'quantity'.
                perc_line.product_uom_qty = 1
                # -------------------------

    # ... (El resto del archivo no necesita cambios) ...
    def action_add_custom_section(self):
        self.ensure_one()
        
        service_refs = [
            'SERV-CAJONES', 'SERV-PLATAFORMA', 'SERV-DESPLAZAMIENTO', 
            'SERV-REPARTO', 'SERV-FABRICACION', 'SERV-MONTAJE'
        ]
        percentage_refs = ['PCT-MUESTRA', 'PCT-BARNIZ', 'PCT-OFITEC', 'PCT-REPASOS']

        products = self.env['product.product'].search([
            ('default_code', 'in', service_refs + percentage_refs)
        ])
        products_by_ref = {p.default_code: p for p in products}
        sequence = max(self.order_line.mapped('sequence') or [0]) + 1
        lines_to_create = []

        lines_to_create.append((0, 0, {
            'order_id': self.id, 'display_type': 'line_section',
            'name': 'NUEVA SECCIÓN (EDITAR TÍTULO)', 'sequence': sequence,
        })); sequence += 1

        for ref in service_refs:
            product = products_by_ref.get(ref)
            if product:
                lines_to_create.append((0, 0, {
                    'order_id': self.id, 'product_id': product.id, 'name': product.name,
                    'product_uom_qty': 1, 'price_unit': product.list_price, 'sequence': sequence,
                })); sequence += 1
        
        lines_to_create.append((0, 0, {
            'order_id': self.id, 'display_type': 'line_note',
            'name': 'Descripción para el presupuesto del cliente...', 'sequence': sequence,
        })); sequence += 1
        
        for ref in percentage_refs:
            product = products_by_ref.get(ref)
            if product:
                lines_to_create.append((0, 0, {
                    'order_id': self.id, 'product_id': product.id, 'name': product.name,
                    'product_uom_qty': 1, 'price_unit': 0, 'sequence': sequence,
                })); sequence += 1
        
        self.update({'order_line': lines_to_create})
        self._recalculate_percentage_lines()
        return True

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_default_code = fields.Char(
        related='product_id.default_code',
        string="Referencia Interna del Producto",
        readonly=True
    )