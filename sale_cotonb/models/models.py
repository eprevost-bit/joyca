from odoo import models, fields, api

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
        
        supplier_lines = {}
        for line in self.order_line.filtered(lambda l: l.product_id.purchase_ok and l.product_id.seller_ids):
            # Usamos el primer proveedor de la lista del producto
            supplier = line.product_id.seller_ids[0].partner_id
            if supplier not in supplier_lines:
                supplier_lines[supplier] = []
            supplier_lines[supplier].append(line)
            
        if not supplier_lines:
            raise UserError(_("No hay productos comprables con proveedores definidos en este presupuesto."))

        purchase_orders_created = self.env['purchase.order']
        
        # Creamos un pedido de compra por cada proveedor
        for supplier, lines in supplier_lines.items():
            po_vals = {
                'partner_id': supplier.id,
                'origin': self.name, # Referencia al pedido de venta
                'order_line': [
                    (0, 0, {
                        'product_id': sol.product_id.id,
                        'product_qty': sol.product_uom_qty,
                        'price_unit': sol.product_id.standard_price, # Usar el costo del producto
                        'date_planned': fields.Datetime.now(),
                    }) for sol in lines
                ]
            }
            purchase_order = self.env['purchase.order'].create(po_vals)
            purchase_orders_created += purchase_order
        self.action_ready_to_ship()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', purchase_orders_created.ids)],
        }

