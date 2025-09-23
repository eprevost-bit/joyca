from odoo import models, api


class PurchaseOrderCustom(models.Model):
    _inherit = 'purchase.order'

    def action_send_items_by_email(self):
        """
        Esta es la función para tu nuevo botón.
        Aquí debes agregar la lógica para enviar el correo con las partidas.
        Por ahora, solo imprimirá un mensaje en la consola de Odoo.
        """
        self.ensure_one()
        print(f"--> Se ha presionado el botón 'Enviar partidas por correo electrónico' para el pedido {self.name}")

        # --- AÑADE TU LÓGICA AQUÍ ---
        # Por ejemplo, podrías buscar una plantilla de correo específica,
        # prepararle un contexto con las líneas de pedido (order_line),
        # y enviarla.
        # -----------------------------

        return True