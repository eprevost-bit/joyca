# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.misc import format_date


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    downpayment_concept_id = fields.Many2one(
        'downpayment.concept',
        string='Concepto del Anticipo',
        help="Selecciona el concepto que se usará como descripción en la factura de anticipo.",
        default=lambda self: self._default_downpayment_concept()
    )

    @api.model
    def _default_downpayment_concept(self):
         #seguimos""" Asigna un concepto por defecto basado en si ya existen facturas de anticipo. """


        active_id = self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'sale.order' and active_id:
            sale_order = self.env['sale.order'].browse(active_id)
            downpayment_invoices = sale_order.invoice_ids.filtered(
                lambda inv: inv.state != 'cancel' and any(line.is_downpayment for line in inv.invoice_line_ids)
            )

            if not downpayment_invoices:
                return self.env.ref('custom_sale_downpayment.dp_concept_first', raise_if_not_found=False)
            else:
                return self.env.ref('custom_sale_downpayment.dp_concept_second', raise_if_not_found=False)
        return False

    def create_invoices(self):

        action = super().create_invoices()

        # Si se seleccionó un concepto, procedemos a modificar la factura recién creada.
        if self.advance_payment_method in ('fixed', 'percentage') and self.downpayment_concept_id:
            # El asistente puede funcionar para varios pedidos, así que iteramos.
            for order in self.sale_order_ids:
                # Buscamos la factura más reciente creada para este pedido.
                # Filtramos por facturas que no estén canceladas y ordenamos por ID descendente.
                newest_invoice = order.invoice_ids.filtered(lambda inv: inv.state != 'cancel').sorted('id',
                                                                                                      reverse=True)
                if not newest_invoice:
                    continue

                invoice = newest_invoice[0]  # La primera de la lista es la más nueva.

                # Encontramos la línea de anticipo dentro de esta factura.
                downpayment_line = invoice.invoice_line_ids.filtered(lambda line: line.is_downpayment)

                if downpayment_line:
                    # Preparamos la descripción personalizada que definimos en el concepto.
                    description = self.downpayment_concept_id.invoice_description.format(
                        order_name=order.name,
                        order_date=format_date(self.env, order.date_order)
                    )
                    # Actualizamos el nombre de la línea (tomamos solo la primera por seguridad).
                    downpayment_line[0].name = description

        return action