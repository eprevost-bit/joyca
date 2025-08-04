from odoo import models, fields, api, _
from odoo.exceptions import UserError

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
        Heredamos la acción de confirmar estándar.
        Primero se ejecuta la lógica original y LUEGO actualizamos nuestro estado.
        """
        res = super(SaleOrder, self).action_confirm()
        self.write({'custom_state': 'confirmed'})
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
                
                
                
                
        