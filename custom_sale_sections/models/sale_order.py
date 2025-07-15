from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Este campo relacionado es la clave para que la vista XML pueda
    # identificar qué líneas bloquear.
    product_default_code = fields.Char(
        related='product_id.default_code',
        string="Referencia Interna del Producto",
        store=True # Usar store=True es una buena práctica para campos relacionados usados en dominios/attrs
    )

# ------------------------------------------------------------------
# Modelo de Pedido de Venta: Contiene toda la lógica principal
# ------------------------------------------------------------------
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_add_custom_section(self):
        """
        Añade una estructura de sección completa al pedido de venta,
        incluyendo servicios fijos y líneas de costes porcentuales.
        """
        self.ensure_one()
        
        # --- Búsqueda de productos ---
        # Referencias de servicios fijos y productos porcentuales
        service_refs = [
            'SERV-CAJONES', 'SERV-PLATAFORMA', 'SERV-DESPLAZAMIENTO', 
            'SERV-REPARTO', 'SERV-FABRICACION', 'SERV-MONTAJE'
        ]
        percentage_refs = ['PCT-MUESTRA', 'PCT-BARNIZ', 'PCT-OFITEC', 'PCT-REPASOS']

        all_refs = service_refs + percentage_refs
        products = self.env['product.product'].search([('default_code', 'in', all_refs)])
        products_by_ref = {p.default_code: p for p in products}

        # Verificar si faltan productos
        missing_refs = [ref for ref in all_refs if ref not in products_by_ref]
        if missing_refs:
            raise UserError(f"No se encontraron los siguientes productos necesarios: {', '.join(missing_refs)}. "
                            "Por favor, créalos o asegúrate de que su 'Referencia Interna' sea correcta.")

        # --- Creación de líneas ---
        sequence = max(self.order_line.mapped('sequence') or [0]) + 1
        lines_to_create = []

        # 1. Título de la sección
        lines_to_create.append((0, 0, {
            'display_type': 'line_section',
            'name': 'NUEVA SECCIÓN (HAZ CLIC PARA EDITAR)',
            'sequence': sequence,
        })); sequence += 1

        # 2. Líneas de servicios fijos
        for ref in service_refs:
            product = products_by_ref[ref]
            lines_to_create.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': product.list_price, # Precio por defecto del producto
                'sequence': sequence,
            })); sequence += 1
        
        # 3. Nota para el presupuesto
        lines_to_create.append((0, 0, {
            'display_type': 'line_note',
            'name': 'Aquí puedes añadir la descripción que verá el cliente en el presupuesto...',
            'sequence': sequence,
        })); sequence += 1
        
        # 4. Líneas de costes porcentuales
        for ref in percentage_refs:
            product = products_by_ref[ref]
            lines_to_create.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': 0, # El precio se calculará con el onchange
                'sequence': sequence,
            })); sequence += 1
            
        self.order_line = lines_to_create
        # Forzar el recálculo inmediato
        self._recalculate_percentage_lines()
        return True

    @api.onchange('order_line')
    def _recalculate_percentage_lines(self):
        """
        Recalcula el precio de las líneas porcentuales basándose en el
        subtotal de los productos estándar dentro de la misma sección.
        """
        sections = {}
        current_section_id = None
        for line in self.order_line:
            if line.display_type == 'line_section':
                # Al encontrar una sección, la registramos
                current_section_id = line.id
                sections[current_section_id] = {'subtotal': 0.0, 'percentage_lines': []}
                continue # Continuar a la siguiente línea

            if not current_section_id:
                continue # Ignorar líneas que no están bajo ninguna sección

            # Si es una línea de coste porcentual, la guardamos para procesarla después
            if line.product_id.default_code and line.product_id.default_code.startswith('PCT-'):
                sections[current_section_id]['percentage_lines'].append(line)
            # Si es un producto normal (no una nota ni sección), sumamos su subtotal
            elif line.display_type is False:
                sections[current_section_id]['subtotal'] += line.price_subtotal

        # Finalmente, actualizamos los precios de las líneas porcentuales
        for section_id, data in sections.items():
            section_subtotal = data['subtotal']
            for perc_line in data['percentage_lines']:
                # Obtenemos el porcentaje del producto (ej: 0.15 para 15%)
                percentage = perc_line.product_id.product_tmpl_id.x_section_percentage or 0.0
                
                # Actualizamos el precio y nos aseguramos que la cantidad sea 1
                perc_line.price_unit = section_subtotal * percentage
                perc_line.product_uom_qty = 1
                
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'

#     @api.onchange('order_line')
#     def _recalculate_percentage_lines(self):
#         sections = {}
#         current_section_id = None
#         for line in self.order_line:
#             if line.display_type == 'line_section':
#                 current_section_id = line.id
#                 sections[current_section_id] = {'subtotal': 0.0, 'percentage_lines': []}
#             elif current_section_id:
#                 if line.product_id.default_code and line.product_id.default_code.startswith('PCT-'):
#                     sections[current_section_id]['percentage_lines'].append(line)
#                 elif line.display_type not in ['line_note']:
#                     sections[current_section_id]['subtotal'] += line.price_subtotal

#         for section_id, data in sections.items():
#             section_subtotal = data['subtotal']
#             for perc_line in data['percentage_lines']:
#                 percentage = perc_line.product_id.x_section_percentage or 0.0
#                 perc_line.price_unit = section_subtotal * percentage
                
#                 # --- CORRECCIÓN CLAVE AQUÍ ---
#                 # El campo correcto para la cantidad es 'product_uom_qty', no 'quantity'.
#                 perc_line.product_uom_qty = 1
#                 # -------------------------

#     # ... (El resto del archivo no necesita cambios) ...
#     def action_add_custom_section(self):
#         self.ensure_one()
        
#         service_refs = [
#             'SERV-CAJONES', 'SERV-PLATAFORMA', 'SERV-DESPLAZAMIENTO', 
#             'SERV-REPARTO', 'SERV-FABRICACION', 'SERV-MONTAJE'
#         ]
#         percentage_refs = ['PCT-MUESTRA', 'PCT-BARNIZ', 'PCT-OFITEC', 'PCT-REPASOS']

#         products = self.env['product.product'].search([
#             ('default_code', 'in', service_refs + percentage_refs)
#         ])
#         products_by_ref = {p.default_code: p for p in products}
#         sequence = max(self.order_line.mapped('sequence') or [0]) + 1
#         lines_to_create = []

#         lines_to_create.append((0, 0, {
#             'order_id': self.id, 'display_type': 'line_section',
#             'name': 'NUEVA SECCIÓN (EDITAR TÍTULO)', 'sequence': sequence,
#         })); sequence += 1

#         for ref in service_refs:
#             product = products_by_ref.get(ref)
#             if product:
#                 lines_to_create.append((0, 0, {
#                     'order_id': self.id, 'product_id': product.id, 'name': product.name,
#                     'product_uom_qty': 1, 'price_unit': product.list_price, 'sequence': sequence,
#                 })); sequence += 1
        
#         lines_to_create.append((0, 0, {
#             'order_id': self.id, 'display_type': 'line_note',
#             'name': 'Descripción para el presupuesto del cliente...', 'sequence': sequence,
#         })); sequence += 1
        
#         for ref in percentage_refs:
#             product = products_by_ref.get(ref)
#             if product:
#                 lines_to_create.append((0, 0, {
#                     'order_id': self.id, 'product_id': product.id, 'name': product.name,
#                     'product_uom_qty': 1, 'price_unit': 0, 'sequence': sequence,
#                 })); sequence += 1
        
#         self.update({'order_line': lines_to_create})
#         self._recalculate_percentage_lines()
#         return True

# class SaleOrderLine(models.Model):
#     _inherit = 'sale.order.line'

#     product_default_code = fields.Char(
#         related='product_id.default_code',
#         string="Referencia Interna del Producto",
#         readonly=True
#     )