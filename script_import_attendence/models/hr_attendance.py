import base64
import io
import pandas as pd
import re
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductImportWizard(models.TransientModel):
    _name = 'product.import.wizard'
    _description = 'Asistente para Importación de Productos desde Excel'

    excel_file = fields.Binary(
        string="Archivo Excel (.xlsx)",
        required=True
    )
    excel_filename = fields.Char(string="Nombre del Archivo")

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string="Lista de Precios para Condiciones",
        required=True,
        help="Las reglas de precios por cantidad se crearán en esta lista de precios."
    )

    def action_import_products(self):
        if not self.excel_file:
            raise UserError("Por favor, suba un archivo de Excel.")
        if not self.excel_filename.endswith('.xlsx'):
            raise UserError("El archivo debe ser un .xlsx")

        try:
            file_data = base64.b64decode(self.excel_file)
            stream = io.BytesIO(file_data)
            df = pd.read_excel(stream, sheet_name='TARIFAS', dtype=str)
        except Exception as e:
            raise UserError(f"Error al leer el archivo Excel: {e}")

        ProductTemplate = self.env['product.template']
        ProductCategory = self.env['product.category']
        PricelistItem = self.env['product.pricelist.item']

        current_category_id = None

        for index, row in df.iterrows():
            nombre_o_categoria = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else None
            precio_coste_str = str(row.iloc[1]) if not pd.isna(row.iloc[1]) else None # Renombrado para claridad

            # --- LÓGICA PARA DETECTAR CATEGORÍAS ---
            if nombre_o_categoria and not precio_coste_str:
                category = ProductCategory.search([('name', '=', nombre_o_categoria)], limit=1)
                if not category:
                    category = ProductCategory.create({'name': nombre_o_categoria})
                current_category_id = category.id
                continue
            
            if not nombre_o_categoria:
                continue

            # --- LÓGICA PARA PROCESAR PRODUCTOS ---
            try:
                # --- MODIFICADO: Ahora leemos el coste del producto ---
                costo_producto = 0.0 if not precio_coste_str else float(precio_coste_str.replace(',', '.'))
                
                # --- NUEVO: Calculamos el precio de venta ---
                precio_venta = costo_producto * 1.3
                
                cantidad_condicional = None
                cantidad_texto = row.iloc[2]
                if not pd.isna(cantidad_texto):
                    match = re.search(r'\d+', str(cantidad_texto))
                    if match:
                        cantidad_condicional = int(match.group(0))

                precio_condicional = None
                if not pd.isna(row.iloc[3]):
                    precio_condicional = float(str(row.iloc[3]).replace(',', '.'))
            
            except (ValueError, TypeError):
                raise UserError(f"Error en la fila {index + 2} del Excel. Verifique que los precios sean números válidos.")

            # --- MODIFICADO: Preparamos los valores correctos para el producto ---
            vals = {
                'name': nombre_o_categoria,
                # 1. Guardamos el coste en 'standard_price'
                'standard_price': costo_producto,
                # 2. Guardamos el precio de venta calculado en 'list_price'
                'list_price': precio_venta,
                # 3. Definimos el producto como 'Almacenable' ('product') para rastrear inventario
                'type': 'consu',
                'categ_id': current_category_id,
            }
            
            product_template = ProductTemplate.search([('name', '=', nombre_o_categoria)], limit=1)
            if product_template:
                product_template.write(vals)
            else:
                product_template = ProductTemplate.create(vals)

            # Lógica para las reglas de precios (sin cambios)
            if product_template and cantidad_condicional is not None and precio_condicional is not None:
                PricelistItem.create({
                    'pricelist_id': self.pricelist_id.id,
                    'applied_on': '1_product',
                    'product_tmpl_id': product_template.id,
                    'min_quantity': cantidad_condicional,
                    'fixed_price': precio_condicional,
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Importación Exitosa',
                'message': 'Los productos y tarifas han sido importados correctamente.',
                'type': 'success',
                'sticky': False,
            }
        }