from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re


import logging

_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    provider_cost = fields.Float(
        string="Coste Proveedor",
        compute='_compute_provider_cost',
        currency_field='currency_id',  # Añade esto para el manejo de moneda
        store=True,
        readonly=True,
    )

    coste_estimado = fields.Float(
        string="Coste Estimado",
        compute='_compute_coste_estimado',  # <-- CAMBIO AQUÍ
        store=True,
        readonly=True,
    )



    @api.depends('product_id')
    def _compute_coste_estimado(self):
        """
        Obtiene el precio estándar del producto usando el ORM.
        """
        for line in self:
            # El ORM de Odoo se encarga de obtener el valor numérico correcto.
            if line.product_id:
                line.coste_estimado = line.product_id.standard_price
            else:
                line.coste_estimado = 0.0

    margen_estimado = fields.Float(
        string="Margen %",
        compute='_compute_margen_estimado',  # Asignamos la nueva función
        store=True,
        readonly=True,
        help="Calcula el margen basado en el coste real (si existe) o el coste estándar del producto."
    )



    @api.depends('price_unit', 'provider_cost', 'coste_estimado')
    def _compute_margen_estimado(self):
        """
        Calcula el margen porcentual de la línea de venta.
        - Si existe un 'provider_cost' (coste real), lo usa como base.
        - Si no, usa el 'coste_estimado' (coste estándar del producto).
        """
        for line in self:
            # Primero, decidimos qué coste vamos a usar
            if line.provider_cost > 0:
                costo = line.provider_cost
            else:
                costo = line.coste_estimado

            # ¡Importante! Evitamos la división por cero si el coste es 0
            if costo > 0:
                beneficio = line.price_unit - costo
                # Fórmula del margen: (Beneficio / Costo) * 100
                margen = (beneficio / costo) * 100
                line.margen_estimado = margen
            else:
                # Si no hay coste, no podemos calcular el margen.
                line.margen_estimado = 0.0


    @api.depends('order_id.name', 'order_id.purchase_order_count', 'product_id')
    def _compute_provider_cost(self):
        """
        Calcula el coste de proveedor para CADA línea de venta.
        Primero, encuentra las POs asociadas al pedido de venta.
        Luego, dentro de esas POs, busca una línea de compra con el MISMO PRODUCTO.
        """
        # Buscamos los pedidos de venta de todas las líneas de una sola vez para optimizar
        for line in self:
            line.provider_cost = 0.0

        for order in self.mapped('order_id'):

            purchase_orders = self.env['purchase.order'].search([
                ('origin', '=', order.name)
            ])

            # Si no hay órdenes de compra para este pedido, no hacemos nada más
            if not purchase_orders:
                continue

            # Ahora, para cada línea de este pedido de venta
            for line in self.filtered(lambda l: l.order_id == order):

                # Buscamos dentro de las POs encontradas una línea con el mismo producto
                # Esto es más robusto que depender de un campo de enlace directo
                purchase_line = self.env['purchase.order.line'].search([
                    ('order_id', 'in', purchase_orders.ids),
                    ('product_id', '=', line.product_id.id),
                ], limit=1)  # Tomamos la primera que encontremos

                if purchase_line:
                    # ¡CORREGIDO! Asignamos el valor numérico (float) directamente.
                    # Ya no formateamos el texto aquí.
                    line.provider_cost = purchase_line.price_subtotal

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

    total_margin = fields.Float(
        string="Margen Total %",  # El string base ya no es tan importante
        compute='_compute_total_margin',
        store=True,
        readonly=True,
    )

    # 1. Añadimos el nuevo campo para la etiqueta dinámica
    total_margin_label = fields.Char(
        string="Etiqueta del Margen",
        compute='_compute_total_margin',
        store=True,
    )

    has_purchasable_products = fields.Boolean(
        string="Tiene productos para comprar",
        compute='_compute_has_purchasable_products'
    )

    @api.depends('order_line.product_id.purchase_ok')
    def _compute_has_purchasable_products(self):
        # El 'self' aquí es un registro de sale.order, que SÍ tiene 'order_line'
        for order in self:
            order.has_purchasable_products = any(line.product_id.purchase_ok for line in order.order_line)

    @api.depends('order_line.provider_cost', 'order_line.coste_estimado', 'amount_untaxed')
    def _compute_total_margin(self):
        for order in self:
            if not order.order_line:
                order.total_margin = 0.0
                order.total_margin_label = _("Margen Total %")  # Etiqueta por defecto
                continue

            use_estimated_cost = any(line.provider_cost == 0.0 for line in order.order_line)

            if use_estimated_cost:
                # 2. Asignamos la etiqueta para el margen estimado
                order.total_margin_label = _("Margen Estimado %")
                total_cost = sum(line.coste_estimado * line.product_uom_qty for line in order.order_line)
            else:
                # 3. Asignamos la etiqueta para el margen real
                order.total_margin_label = _("Margen Total %")
                total_cost = sum(line.provider_cost * line.product_uom_qty for line in order.order_line)

            if total_cost > 0:
                profit = order.amount_untaxed - total_cost
                margin = (profit / total_cost) * 100
                order.total_margin = margin
            else:
                order.total_margin = 0.0
    
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
        products_without_cost = []

        # Recorremos cada línea del presupuesto de venta (self.order_line)
        for line in self.order_line:
            # Condición 1: El producto se puede comprar (es un producto de compra)
            # Condición 2: El coste del proveedor es 0 (no se ha asignado)
            # Condición 3: El producto NO es el de honorarios (excepción)
            if line.product_id.purchase_ok and line.provider_cost == 0 and line.product_id.default_code != 'honorario':
                # Si se cumplen las tres condiciones, añadimos el nombre del producto a la lista.
                products_without_cost.append(line.product_id.name)

        # Si la lista NO está vacía, significa que encontramos productos que bloquean la confirmación.
        if products_without_cost:
            # Creamos un mensaje de error claro para el usuario.
            error_message = (
                "No se puede confirmar el pedido. \n\n"
                "Los siguientes productos son de compra y no tienen un coste de proveedor asignado:\n"
                f"- {', '.join(products_without_cost)}\n\n"
                "Por favor, actualiza los precios desde los presupuestos de compra o asigna un proveedor en la ficha del producto."
            )
            # Lanzamos una excepción ValidationError que mostrará el mensaje en un diálogo.
            raise ValidationError(error_message)

        res = super(SaleOrder, self).action_confirm()

        self.write({'custom_state': 'confirmed'})
        project = self.order_line.mapped('project_id')
        if project:
            # 3. Si se encontró un proyecto, abrimos nuestro asistente
            return {
                'name': _('Asignar Nombre al Proyecto'),
                'type': 'ir.actions.act_window',
                'res_model': 'rename.project.wizard',
                'view_mode': 'form',
                'target': 'new',  # Para que se abra como una ventana emergente
                'context': {
                    # Le pasamos los datos al asistente
                    'default_project_id': project[0].id,
                    'default_name': project[0].name,
                }
            }


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
                provider_cost = po_line.price_subtotal
                sale_line.write({'provider_cost': provider_cost})
                if sale_line.price_unit != new_price:
                    sale_line.write({'price_unit': new_price})
                    _logger.info(
                        f"Precio actualizado para '{product.display_name}' en la línea de venta ID {sale_line.id}. "
                        f"Costo: {po_line.price_unit}, Nuevo Precio Venta: {new_price:.2f}"
                    )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Proceso Completado'),
                'message': _('Las órdenes de compra y los precios han sido actualizados.'),
                'type': 'success',
                'sticky': False,

                # La acción de refresco va anidada aquí.
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'res_id': self.id,
                    'views': [[False, 'form']],

                    'target': 'current',
                }
            }
        }
