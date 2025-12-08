import base64
import io
import pandas as pd
from odoo import models, fields, api
from odoo.exceptions import UserError


class PartnerImportWizard(models.TransientModel):
    _name = 'partner.import.wizard'
    _description = 'Asistente para Importación de Contactos'

    excel_file = fields.Binary(string="Archivo Excel (.xlsx)", required=True)
    excel_filename = fields.Char(string="Nombre del Archivo")

    def action_import_partners(self):
        if not self.excel_file:
            raise UserError("Por favor, suba un archivo de Excel.")

        try:
            file_data = base64.b64decode(self.excel_file)
            stream = io.BytesIO(file_data)
            # Asumimos que la hoja se llama 'CONTACTOS' o leemos la primera
            df = pd.read_excel(stream, dtype=str)
        except Exception as e:
            raise UserError(f"Error al leer el archivo Excel: {e}")

        ResPartner = self.env['res.partner']
        PartnerLine = self.env['res.partner.line']
        PartnerCategory = self.env['res.partner.category']  # Etiquetas

        for index, row in df.iterrows():
            # 1. Columna A: Empresa (Nombre)
            nombre_empresa = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else None

            if not nombre_empresa:
                continue  # Saltamos filas vacías

            # 2. Columna B: Línea (Busca o Crea en el nuevo modelo)
            line_id = False
            nombre_linea = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else None

            if nombre_linea:
                # Buscamos si existe la línea, si no, la creamos (para que la importación no falle)
                line_obj = PartnerLine.search([('name', '=', nombre_linea)], limit=1)
                if not line_obj:
                    line_obj = PartnerLine.create({'name': nombre_linea})
                line_id = line_obj.id

            # 3. Columna C: Descripción -> Etiquetas separadas por "-"
            tag_ids = []
            raw_tags = str(row.iloc[2]) if not pd.isna(row.iloc[2]) else ""

            if raw_tags:
                # Separamos por guión y quitamos espacios en blanco
                etiquetas = [t.strip() for t in raw_tags.split('-') if t.strip()]

                for etiqueta_nombre in etiquetas:
                    tag = PartnerCategory.search([('name', '=', etiqueta_nombre)], limit=1)
                    if not tag:
                        tag = PartnerCategory.create({'name': etiqueta_nombre})
                    tag_ids.append(tag.id)

            # --- CREACIÓN O ACTUALIZACIÓN DEL CONTACTO ---
            vals = {
                'name': nombre_empresa,
                'is_company': True,  # Siempre es compañía
                'line_id': line_id,  # El campo Many2one nuevo
                'category_id': [(6, 0, tag_ids)],  # Asignación de etiquetas Many2many
            }

            # Buscamos si ya existe por nombre para no duplicar (opcional)
            partner = ResPartner.search([('name', '=', nombre_empresa)], limit=1)
            if partner:
                partner.write(vals)
            else:
                ResPartner.create(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Importación Exitosa',
                'message': 'Las empresas han sido importadas correctamente.',
                'type': 'success',
                'sticky': False,
            }
        }