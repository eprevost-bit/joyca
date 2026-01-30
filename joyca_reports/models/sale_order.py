# -*- coding: utf-8 -*-

from odoo import models, fields, api
from pypdf import PdfReader, PdfWriter
import base64
import logging
import io

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_paged_content(self, text_content):
        """
        Esta función toma un texto largo y lo divide en una lista de textos,
        donde cada uno cabe aproximadamente en una página.
        """
        if not text_content:
            return []

        # --- AJUSTA ESTE NÚMERO ---
        # Si el texto se corta muy pronto, aumenta este número (ej. 3000).
        # Si el texto se sale de la página, redúcelo (ej. 2600).
        CHARS_PER_PAGE = 2800

        pages = []
        current_page = ""
        paragraphs = text_content.split('\n')

        for p in paragraphs:
            if len(p) > CHARS_PER_PAGE:
                words = p.split(' ')
                line = ""
                for word in words:
                    if len(line) + len(word) + 1 > CHARS_PER_PAGE:
                        pages.append(line)
                        line = word + " "
                    else:
                        line += word + " "
                if line:
                    pages.append(line)
                continue

            if len(current_page) + len(p) + 1 > CHARS_PER_PAGE:
                pages.append(current_page)
                current_page = p + '\n'
            else:
                current_page += p + '\n'

        if current_page:
            pages.append(current_page)

        return pages

    """def action_debug_count_pages(self):
        self.ensure_one()


        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            'joyca_reports.report_sale_custom_standalone',
            self.id
        )


        reader = PdfReader(io.BytesIO(pdf_content))
        total_pages = len(reader.pages)

        _logger.warning(
            "Presupuesto %s: total_paginas=%s",
            self.name,
            total_pages
        )


        pdf_content = self._write_total_pages_first_page(
            pdf_content,
            total_pages
        )


        attachment = self.env['ir.attachment'].create({
            'name': f'Presupuesto_{self.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'sale.order',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })


        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _write_total_pages_first_page(self, pdf_content, total_pages):
        from pypdf import PdfReader, PdfWriter, Transformation
        from reportlab.pdfgen import canvas
        import io

        reader = PdfReader(io.BytesIO(pdf_content))
        writer = PdfWriter()

        for index, page in enumerate(reader.pages):
            if index == 0:
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)

                packet = io.BytesIO()
                c = canvas.Canvas(packet, pagesize=(width, height))
                c.setFont("Helvetica-Bold", 9)

                c.drawString(510, 590, str(total_pages))

                c.save()
                packet.seek(0)

                overlay = PdfReader(packet).pages[0]

                page.merge_transformed_page(
                    overlay,
                    Transformation().translate(0, 0),
                    over=True
                )

            writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()"""



