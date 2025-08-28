from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import UserError


import logging

_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    provider_cost = fields.Char(
        string="Coste Proveedor",
        compute='_compute_provider_cost',
        store=False,  # No es necesario guardarlo en la base de datos
    )

    @api.depends('order_id.name', 'order_id.purchase_order_count', 'product_id')
    def _compute_provider_cost(self):
        """
        Calcula el coste de proveedor para CADA línea de venta.
        Primero, encuentra las POs asociadas al pedido de venta.
        Luego, dentro de esas POs, busca una línea de compra con el MISMO PRODUCTO.
        """
        # Buscamos los pedidos de venta de todas las líneas de una sola vez para optimizar
        for order in self.mapped('order_id'):
            # Encontramos todas las POs relacionadas a este pedido de venta
            purchase_orders = self.env['purchase.order'].search([
                ('origin', '=', order.name)
            ])

            # Si no hay órdenes de compra para este pedido, no hacemos nada más
            if not purchase_orders:
                continue

            # Ahora, para cada línea de este pedido de venta
            for line in self.filtered(lambda l: l.order_id == order):
                # Valor por defecto
                line.provider_cost = "Pendiente"

                # Buscamos dentro de las POs encontradas una línea con el mismo producto
                # Esto es más robusto que depender de un campo de enlace directo
                purchase_line = self.env['purchase.order.line'].search([
                    ('order_id', 'in', purchase_orders.ids),
                    ('product_id', '=', line.product_id.id),
                ], limit=1)  # Tomamos la primera que encontremos

                if purchase_line:
                    # ¡Encontrada! Usamos su subtotal y moneda
                    cost = purchase_line.price_subtotal
                    currency = purchase_line.currency_id
                    line.provider_cost = f"{cost:.2f} {currency.symbol or ''}".strip()

    # @api.depends('order_id.name', 'order_id.purchase_order_count')
    # def _compute_provider_cost(self):
    #     """
    #     Calcula el coste buscando el pedido de compra (PO) asociado
    #     y muestra el TOTAL de ese PO en la línea de venta.
    #     """
    #     for line in self:
    #         # Valor por defecto
    #         line.provider_cost = "Pendiente"
    #
    #         # Solo necesitamos el nombre del pedido de venta
    #         if not line.order_id.name:
    #             continue
    #
    #         # CORRECTO: Buscamos en 'purchase.order' usando el campo 'origin'
    #         # y la referencia 'line.order_id.name'
    #         purchase_order = self.env['purchase.order'].search([
    #             ('origin', '=', line.order_id.name),
    #         ], limit=1)
    #
    #         if purchase_order:
    #             # Si se encuentra la orden de compra, usamos su 'amount_total'.
    #             cost = purchase_order.amount_total
    #             currency = purchase_order.currency_id
    #             # Formateamos el resultado
    #             line.provider_cost = f"{cost:.2f} {currency.symbol or ''}".strip()

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # 1. El campo de estado personalizado que ya teníamos.
    custom_state = fields.Selection([
        ('draft', 'Borrador'),
        ('waiting_purchase', 'A la espera de compras'),
        ('ready', 'Listo para enviar'),
        ('sent', 'Enviado'),
        ('confirmed', 'Confirmado'),
    ], string='Estado Personalizado', default='draft', readonly=True, copy=False, tracking=True)
    
    purchase_order_count = fields.Integer(
        string="Órdenes de Compra",
        compute='_compute_purchase_order_count',
        readonly=True
    )
    
    project_count = fields.Integer(
        string="Proyectos",
        compute='_compute_project_count',
        readonly=True
    )
    
    def _compute_project_count(self):
        for order in self:
            # Busca en 'project.project' en lugar de 'purchase.order'
            order.project_count = self.env['project.project'].search_count(
                [('name', '=', order.name)]
            )
    def action_view_projects(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proyectos',
            'res_model': 'project.project',
            'view_mode': 'kanban,form,list',
            'domain': [('name', '=', 'Proyecto_'+self.name)],
            'target': 'current',
        }
    def _compute_purchase_order_count(self):
        """
        Calcula el número de órdenes de compra creadas a partir de esta venta.
        """
        for order in self:
            # Usamos search_count para una mayor eficiencia.
            # Busca en 'purchase.order' todos los registros cuyo campo 'origin'
            # sea igual al nombre (referencia) de este pedido de venta.
            order.purchase_order_count = self.env['purchase.order'].search_count(
                [('origin', '=', order.name)]
            )
    def action_view_purchase_orders(self):
        """
        Esta función es llamada por el botón inteligente.
        Devuelve una acción que muestra la vista de lista de las
        órdenes de compra relacionadas.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Órdenes de Compra'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)], # Filtra para mostrar solo las PO de esta SO
            'target': 'current',
        }


    # 2. Funciones para los botones de nuestro flujo personalizado.
    def action_waiting_purchase(self):
        """ Pasa el estado a 'A la espera de compras'. """
        self.action_create_purchase_order()
        return self.write({'custom_state': 'waiting_purchase'})

    def action_ready_to_ship(self):
        """ Pasa el estado a 'Listo para enviar'. """
        return self.write({'custom_state': 'ready'})

    def action_mark_as_sent(self):
        """ Pasa el estado a 'Enviado' y también actualiza el estado nativo de Odoo. """
        # Esto asegura que si usas el botón personalizado, Odoo también se entere.
        self.filtered(lambda so: so.state in ('draft',)).action_quotation_sent()
        return self.write({'custom_state': 'sent'})

    def action_reset_to_draft(self):
        """ Permite regresar el estado a 'Borrador'. """
        # También reseteamos el estado nativo de Odoo si es necesario.
        self.action_draft()
        return self.write({'custom_state': 'draft'})

    # --- INTEGRACIÓN CON ACCIONES NATIVAS DE ODOO ---

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        """
        Heredamos message_post para detectar cuándo se envía un correo.
        Cuando el estado nativo pasa a 'sent', actualizamos nuestro estado.
        """
        if self.env.context.get('mark_so_as_sent'):
             self.write({'custom_state': 'sent'})
        return super(SaleOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)


    def action_confirm(self):
        """
        Heredamos la acción de confirmar.
        1. Se ejecuta la lógica original de Odoo.
        2. Se actualiza nuestro estado personalizado.
        3. Se crea un proyecto para la venta.
        4. Se crea una tarea en ese proyecto por cada línea del presupuesto,
        EXCLUYENDO las que son gastos refacturados.
        """
        res = super(SaleOrder, self).action_confirm()

        self.write({'custom_state': 'confirmed'})

        # for order in self:
        #     project = self.env['project.project'].create({
        #         'name': 'Proyecto_'+order.name,
        #         'partner_id': order.partner_id.id,
        #     })
        #
        #     for line in order.order_line:
        #         # Ignorar líneas que son secciones o notas.
        #         if line.display_type:
        #             continue
        #
        #         # **AÑADIR ESTA LÍNEA PARA SOLUCIONAR EL ERROR**
        #         # Ignorar líneas que son gastos refacturados.
        #         if line.is_expense:
        #             continue
        #
        #         self.env['project.task'].create({
        #             'name': line.name,
        #             'project_id': project.id,
        #             'partner_id': order.partner_id.id,
        #             # 'sale_line_id': line.id
        #         })

        return res
    
    def action_create_purchase_order(self):
        self.ensure_one()

        # 1. Buscar al proveedor por defecto llamado "Proveedor Reserva"
        # Asegúrate de que este proveedor exista en tu sistema en "Contactos".
        default_supplier = self.env['res.partner'].search([('name', '=', 'Proveedor Reserva')], limit=1)
        if not default_supplier:
            raise UserError(_("No se pudo encontrar el proveedor por defecto 'Proveedor Reserva'. Por favor, créelo o verifique el nombre."))

        category_lines = {}
        # 2. Filtrar líneas con productos que se puedan comprar y agruparlas por categoría
        for line in self.order_line.filtered(lambda l: l.product_id and l.product_id.purchase_ok):
            category = line.product_id.categ_id
            if not category:
                # Opcional: Omitir productos sin categoría o asignar una por defecto
                continue
            
            if category not in category_lines:
                category_lines[category] = []
            category_lines[category].append(line)
            
        if not category_lines:
            raise UserError(_("No hay productos comprables en este presupuesto para generar órdenes de compra."))

        purchase_orders_created = self.env['purchase.order']
        
        # 3. Crear un pedido de compra por cada categoría de producto
        for category, lines in category_lines.items():
            po_vals = {
                'partner_id': default_supplier.id, # Usar siempre el proveedor por defecto
                'origin': self.name,              # Referencia al pedido de venta
                'notes': _('Orden de compra para productos de la categoría: %s') % category.display_name, # Opcional: Añadir nota
                'order_line': [
                    (0, 0, {
                        'product_id': sol.product_id.id,
                        'product_qty': sol.product_uom_qty,
                        'product_uom': sol.product_id.uom_po_id.id, # Usar la unidad de medida de compra
                        'price_unit': sol.product_id.standard_price, # Usar el costo del producto
                        'date_planned': fields.Datetime.now(),
                        'name': sol.product_id.display_name,
                    }) for sol in lines
                ]
            }
            purchase_order = self.env['purchase.order'].create(po_vals)
            purchase_orders_created += purchase_order

        # 4. Devolver una acción para mostrar las órdenes de compra creadas
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Proceso Completado'),
                'message': _('Las órdenes de compra se han creado exitosamente.'),
                'type': 'success',  
                'sticky': False,
            }
        }
    
    def _check_purchase_orders_status(self):
        """
        Método que verifica si TODAS las órdenes de compra asociadas a esta
        orden de venta ('self') han sido confirmadas. Si es así, avanza el estado.
        Ahora es más eficiente y se llama desde la PO.
        """
        for order in self:
            if order.custom_state != 'waiting_purchase':
                continue

            purchase_orders = self.env['purchase.order'].search([('origin', '=', order.name)])

            if not purchase_orders:
                continue

            # Comprueba si TODAS las POs están en estado 'purchase' o 'done'.
            all_confirmed = all(po.state in ['purchase', 'done', 'intermediate'] for po in purchase_orders)

            if all_confirmed:
                # Si es así, cambia el estado de la SO.
                order.action_ready_to_ship()

    def action_update_purchase_orders(self):
        """
        Sincroniza las órdenes de compra y ACTUALIZA PRECIOS desde la venta.
        1. Elimina las líneas de compra de productos que ya no están en la venta.
        2. Crea nuevas líneas de compra para productos añadidos a la venta.
        3. Actualiza los precios en las líneas de venta basándose en los costes
           actuales de las órdenes de compra.
        """
        self.ensure_one()
        # if self.custom_state != 'waiting_purchase':
        #     raise UserError(_("Solo se pueden actualizar las compras cuando el pedido está 'A la espera de compras'."))

        _logger.info(f"Iniciando sincronización completa para la venta: {self.name}")

        # Obtenemos las órdenes de compra existentes al inicio
        purchase_orders = self.env['purchase.order'].search([('origin', '=', self.name)])
        if not purchase_orders:
            self.action_create_purchase_order()
            # Después de crear, las volvemos a buscar para que el resto del código funcione
            purchase_orders = self.env['purchase.order'].search([('origin', '=', self.name)])
            _logger.info("No se encontraron POs. Se crearon nuevas.")

        # PARTE 1 Y 2 (No cambian, se quedan como estaban)
        current_so_product_ids = {
            line.product_id.id for line in self.order_line.filtered(lambda l: l.product_id and l.product_id.purchase_ok)
        }
        po_lines_map = {line.product_id.id: line for line in purchase_orders.order_line}
        product_ids_to_remove = set(po_lines_map.keys()) - current_so_product_ids

        lines_to_unlink = self.env['purchase.order.line']
        for product_id in product_ids_to_remove:
            po_line = po_lines_map[product_id]
            if po_line.order_id.state in ('purchase', 'done'):
                raise UserError(
                    _("No se puede eliminar la línea del producto '%s' porque la orden de compra %s ya ha sido confirmada.") %
                    (po_line.product_id.display_name, po_line.order_id.name)
                )
            lines_to_unlink += po_line

        if lines_to_unlink:
            affected_purchase_orders = lines_to_unlink.order_id
            lines_to_unlink.unlink()
            _logger.info(f"Se eliminaron {len(lines_to_unlink)} líneas de compra obsoletas.")

            purchase_orders_to_delete = self.env['purchase.order']
            for po in affected_purchase_orders:
                if not po.order_line:
                    purchase_orders_to_delete += po

            if purchase_orders_to_delete:
                po_names = ', '.join(purchase_orders_to_delete.mapped('name'))
                purchase_orders_to_delete.button_cancel()
                purchase_orders_to_delete.unlink()
                _logger.info(f"Se eliminaron las órdenes de compra vacías: {po_names}")

        product_ids_to_add = current_so_product_ids - set(po_lines_map.keys())
        if product_ids_to_add:
            new_lines_by_category = defaultdict(lambda: self.env['sale.order.line'])
            for line in self.order_line:
                if line.product_id.id in product_ids_to_add:
                    category = line.product_id.categ_id
                    new_lines_by_category[category] += line

            default_supplier = self.env['res.partner'].search([('name', '=', 'Proveedor Reserva')], limit=1)
            if not default_supplier:
                raise UserError(_("No se pudo encontrar el proveedor por defecto 'Proveedor Reserva'."))

            for category, so_lines in new_lines_by_category.items():
                existing_po = purchase_orders.filtered(
                    lambda p: p.partner_id == default_supplier and category.display_name in (p.notes or '')
                )
                po_lines_vals = [
                    (0, 0, {
                        'product_id': sol.product_id.id, 'product_qty': sol.product_uom_qty,
                        'product_uom': sol.product_id.uom_po_id.id, 'price_unit': sol.product_id.standard_price,
                        'date_planned': fields.Datetime.now(), 'name': sol.product_id.display_name,
                    }) for sol in so_lines
                ]
                if existing_po:
                    existing_po.write({'order_line': po_lines_vals})
                else:
                    self.env['purchase.order'].create({
                        'partner_id': default_supplier.id, 'origin': self.name,
                        'notes': _('Orden de compra para productos de la categoría: %s') % category.display_name,
                        'order_line': po_lines_vals,
                    })
            _logger.info(f"Se añadieron líneas para {len(product_ids_to_add)} productos nuevos.")

        # --------------------------------------------------------------------
        # PARTE 3: ACTUALIZAR PRECIOS (¡AQUÍ ESTÁ LA CORRECCIÓN!)
        # --------------------------------------------------------------------
        _logger.info("Iniciando actualización de precios en la Venta desde las Compras.")
        all_purchase_orders = self.env['purchase.order'].search([('origin', '=', self.name)])
        # all_purchase_orders.refresh()

        for po_line in all_purchase_orders.order_line:
            product = po_line.product_id
            margin_percent = product.categ_id.margin or 0.0
            margin_decimal = margin_percent / 100.0

            sale_lines_to_update = self.order_line.filtered(
                lambda sol: sol.product_id == product
            )

            for sale_line in sale_lines_to_update:
                new_price = po_line.price_unit * (1 + margin_decimal)
                if sale_line.price_unit != new_price:
                    sale_line.write({'price_unit': new_price})
                    _logger.info(
                        f"Precio actualizado para '{product.display_name}' en la línea de venta ID {sale_line.id}. "
                        f"Costo: {po_line.price_unit}, Nuevo Precio Venta: {new_price:.2f}"
                    )

        # Notificación final (sin cambios)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Proceso Completado'),
                'message': _('Las órdenes de compra y los precios han sido actualizados.'),
                'type': 'success',
                'sticky': False,
            }
        }
    # Reemplaza tu función actual con esta versión corregida

    # def action_update_purchase_orders(self):
    #     """
    #     Sincroniza las órdenes de compra y ACTUALIZA PRECIOS desde la venta.
    #     1. Elimina las líneas de compra de productos que ya no están en la venta.
    #     2. Crea nuevas líneas de compra para productos añadidos a la venta.
    #     3. Actualiza los precios en las líneas de venta basándose en los costes
    #        actuales de las órdenes de compra.
    #     """
    #     self.ensure_one()
    #
    #     _logger.info(f"Iniciando sincronización completa para la venta: {self.name}")
    #
    #     purchase_orders = self.env['purchase.order'].search([('origin', '=', self.name)])
    #     if not purchase_orders:
    #         self.action_create_purchase_order()
    #         _logger.info("No se encontraron POs. Se crearon nuevas.")
    #         return
    #
    #     # PARTE 1 Y 2 (No cambian, se quedan como estaban)
    #     current_so_product_ids = {
    #         line.product_id.id for line in self.order_line.filtered(lambda l: l.product_id and l.product_id.purchase_ok)
    #     }
    #     po_lines_map = {line.product_id.id: line for line in purchase_orders.order_line}
    #     product_ids_to_remove = set(po_lines_map.keys()) - current_so_product_ids
    #
    #     lines_to_unlink = self.env['purchase.order.line']
    #     for product_id in product_ids_to_remove:
    #         po_line = po_lines_map[product_id]
    #         if po_line.order_id.state in ('purchase', 'done'):
    #             raise UserError(
    #                 _("No se puede eliminar la línea del producto '%s' porque la orden de compra %s ya ha sido confirmada.") %
    #                 (po_line.product_id.display_name, po_line.order_id.name)
    #             )
    #         lines_to_unlink += po_line
    #
    #     if lines_to_unlink:
    #         # 1. Antes de borrar las líneas, guardamos una referencia a sus órdenes de compra.
    #         #    Usamos .order_id para obtener un recordset de las órdenes de compra únicas afectadas.
    #         affected_purchase_orders = lines_to_unlink.order_id
    #
    #         # 2. Eliminamos las líneas como antes.
    #         lines_to_unlink.unlink()
    #         _logger.info(f"Se eliminaron {len(lines_to_unlink)} líneas de compra obsoletas.")
    #
    #         # 3. Ahora, buscamos qué órdenes de compra de las afectadas se quedaron sin líneas.
    #         purchase_orders_to_delete = self.env['purchase.order']
    #         for po in affected_purchase_orders:
    #             # Si el campo 'order_line' está vacío, significa que la PO ya no tiene líneas.
    #             if not po.order_line:
    #                 purchase_orders_to_delete += po
    #
    #         # 4. Si encontramos alguna orden de compra vacía, la eliminamos.
    #         if purchase_orders_to_delete:
    #             po_names = ', '.join(purchase_orders_to_delete.mapped('name'))
    #             purchase_orders_to_delete.button_cancel()
    #             purchase_orders_to_delete.unlink()
    #             _logger.info(f"Se eliminaron las órdenes de compra vacías: {po_names}")
    #
    #     product_ids_to_add = current_so_product_ids - set(po_lines_map.keys())
    #     if product_ids_to_add:
    #         new_lines_by_category = defaultdict(lambda: self.env['sale.order.line'])
    #         for line in self.order_line:
    #             if line.product_id.id in product_ids_to_add:
    #                 category = line.product_id.categ_id
    #                 new_lines_by_category[category] += line
    #
    #         default_supplier = self.env['res.partner'].search([('name', '=', 'Proveedor Reserva')], limit=1)
    #         if not default_supplier:
    #             raise UserError(_("No se pudo encontrar el proveedor por defecto 'Proveedor Reserva'."))
    #
    #         for category, so_lines in new_lines_by_category.items():
    #             existing_po = purchase_orders.filtered(
    #                 lambda p: p.partner_id == default_supplier and category.display_name in (p.notes or '')
    #             )
    #             po_lines_vals = [
    #                 (0, 0, {
    #                     'product_id': sol.product_id.id, 'product_qty': sol.product_uom_qty,
    #                     'product_uom': sol.product_id.uom_po_id.id, 'price_unit': sol.product_id.standard_price,
    #                     'date_planned': fields.Datetime.now(), 'name': sol.product_id.display_name,
    #                 }) for sol in so_lines
    #             ]
    #             if existing_po:
    #                 existing_po.write({'order_line': po_lines_vals})
    #             else:
    #                 self.env['purchase.order'].create({
    #                     'partner_id': default_supplier.id, 'origin': self.name,
    #                     'notes': _('Orden de compra para productos de la categoría: %s') % category.display_name,
    #                     'order_line': po_lines_vals,
    #                 })
    #         _logger.info(f"Se añadieron líneas para {len(product_ids_to_add)} productos nuevos.")
    #
    #     # --------------------------------------------------------------------
    #     # PARTE 3: ACTUALIZAR PRECIOS (¡AQUÍ ESTÁ LA CORRECCIÓN!)
    #     # --------------------------------------------------------------------
    #     _logger.info("Iniciando actualización de precios en la Venta desde las Compras.")
    #     all_purchase_orders = self.env['purchase.order'].search([('origin', '=', self.name)])
    #
    #     for po_line in all_purchase_orders.order_line:
    #         product = po_line.product_id
    #         margin_percent = product.categ_id.margin or 0.0
    #         margin_decimal = margin_percent / 100.0
    #
    #         # Renombramos la variable para que sea más claro que pueden ser varias líneas
    #         sale_lines_to_update = self.order_line.filtered(
    #             lambda sol: sol.product_id == product
    #         )
    #
    #         # Si encuentra una o más líneas, las recorremos con un bucle
    #         for sale_line in sale_lines_to_update:
    #             new_price = po_line.price_unit * (1 + margin_decimal)
    #             if sale_line.price_unit != new_price:
    #                 sale_line.write({'price_unit': new_price})  # Actualizamos línea por línea
    #                 _logger.info(
    #                     f"Precio actualizado para '{product.display_name}' en la línea de venta ID {sale_line.id}. "
    #                     f"Costo: {po_line.price_unit}, Nuevo Precio Venta: {new_price:.2f}"
    #                 )
    #
    #     # Notificación final (sin cambios)
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': _('Proceso Completado'),
    #             'message': _('Las órdenes de compra y los precios han sido actualizados.'),
    #             'type': 'success',
    #             'sticky': False,
    #         }
    #     }