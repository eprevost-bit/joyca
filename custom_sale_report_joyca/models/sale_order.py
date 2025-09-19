# -*- coding: utf-8 -*-

from odoo import models, fields, api


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