import re
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ... tu campo 'state' modificado va aquí ...
    state = fields.Selection(
        selection_add=[
            ('version', 'Versión'),
            ('sent',)
        ],
        ondelete={'version': 'cascade'}
    )
    total_manufacturing_hours = fields.Float(
        string="Total Horas Fabricación",
        compute='_compute_total_hours',
        store=True,
        readonly=True,
    )

    # 2. Creamos el campo para el total de horas de montaje
    total_assembly_hours = fields.Float(
        string="Total Horas Montaje",
        compute='_compute_total_hours',
        store=True,
        readonly=True,
    )

    # 3. Creamos la función que calcula ambos totales
    @api.depends('order_line.manufacturing_hours', 'order_line.assembly_hours')
    def _compute_total_hours(self):
        """
        Suma las horas de todas las líneas del pedido.
        """
        for order in self:
            order.total_manufacturing_hours = sum(line.manufacturing_hours for line in order.order_line)
            order.total_assembly_hours = sum(line.assembly_hours for line in order.order_line)

    @api.model_create_multi
    def create(self, vals_list):
        new_orders = super(SaleOrder, self).create(vals_list)

        # 2. Recorremos todos los presupuestos recién creados.
        for order in new_orders:
            # 3. Verificamos que el nombre no tenga ya una versión para evitar duplicados.
            if order.name and '-V' not in order.name:
                # 4. Añadimos el sufijo '-V1' al nombre.
                order.name = f"{order.name}-V1"

        # 5. Devolvemos los registros modificados.
        return new_orders

    def action_create_new_version(self):
        """
        Crea una nueva versión del presupuesto (V2, V3...).
        Si se está creando la V2, la V1 pasará a estado 'version'.
        Para versiones posteriores (V3, V4...), no se cambia el estado de las anteriores.
        """
        self.ensure_one()

        # 1. Determinar el nombre base del presupuesto (ej: 'S00025')
        base_name_match = re.match(r'^(.*?)(?:-V(\d+))?$', self.name)
        base_name = base_name_match.groups()[0] if base_name_match else self.name

        # 2. Buscar todos los presupuestos relacionados para encontrar el número de versión más alto
        related_orders = self.env['sale.order'].search([
            ('name', '=like', f"{base_name}-V%")
        ])

        max_version = 0
        for order in related_orders:
            version_match = re.search(r'-V(\d+)$', order.name)
            if version_match:
                max_version = max(max_version, int(version_match.group(1)))

        new_version_number = max_version + 1

        # 3. Crear la nueva versión como una copia del presupuesto actual.
        new_quotation = self.copy(default={
            'name': f"{base_name}-V{new_version_number}",
            'state': 'draft',
            'origin': self.name,
        })

        # --- INICIO DE LA LÓGICA CORREGIDA ---

        # 4. Buscamos el presupuesto V1 de esta secuencia.
        v1_order = self.env['sale.order'].search([('name', '=', f"{base_name}-V1")], limit=1)

        # 5. Si la V1 existe y su estado aún no es 'version', lo actualizamos.
        #    Esto asegura que SÓLO la V1 cambie de estado, y sólo una vez.
        if v1_order and v1_order.state != 'version':
            v1_order.write({'state': 'version'})

        # --- FIN DE LA LÓGICA CORREGIDA ---

        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva Versión'),
            'res_model': 'sale.order',
            'res_id': new_quotation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        for order in self:
            # 1. Validamos que exista un proyecto antes de hacer nada.
            if not order.project_id:
                raise ValidationError(_(
                    "No se puede confirmar el pedido '%s'.\n\nPor favor, seleccione un proyecto antes de continuar.",
                    order.name
                ))

            total_manufacturing_hours = 0.0
            total_assembly_hours = 0.0
            # AÑADIMOS: Una variable para acumular el total de horas asignadas.
            total_allocated_hours = 0.0

            # 2. Recorremos CADA LÍNEA para crear su estructura de tareas.
            for line in order.order_line:
                # Omitimos líneas que no son productos (ej: secciones, notas, gastos)
                if line.display_type or line.is_expense:
                    continue

                # --- Lógica para crear la TAREA CONTENEDORA (sin horas) ---
                parent_task_values = {
                    'name': f"{line.product_id.name}",  # Nombre del producto
                    'project_id': order.project_id.id,
                    'partner_id': order.partner_id.id,
                    'allocated_hours': line.manufacturing_hours + line.assembly_hours,
                    'description': f"Tarea principal para el producto: {line.name}\nde la orden de venta: {order.name}",
                    # Nota: No asignamos 'allocated_hours' aquí.
                }

                # Creamos la tarea principal y la guardamos para usar su ID.
                parent_task = self.env['project.task'].create(parent_task_values)

                # --- ¡NUEVO! Crear Subtarea de Fabricación ---
                # Solo la creamos si hay horas de fabricación.
                if line.manufacturing_hours > 0:
                    fabrication_subtask_values = {
                        'name': f"Fabricación - {line.product_id.name}",
                        'project_id': order.project_id.id,
                        'partner_id': order.partner_id.id,
                        'parent_id': parent_task.id,  # <-- Vínculo a la tarea principal
                        'allocated_hours': line.manufacturing_hours,
                        'description': "Subtarea de fabricación.",
                    }
                    self.env['project.task'].create(fabrication_subtask_values)

                # --- Crear Subtarea de Montaje ---
                # Solo la creamos si hay horas de montaje.
                if line.assembly_hours > 0:
                    assembly_subtask_values = {
                        'name': f"Montaje - {line.product_id.name}",
                        'project_id': order.project_id.id,
                        'partner_id': order.partner_id.id,
                        'parent_id': parent_task.id,  # <-- Vínculo a la tarea principal
                        'allocated_hours': line.assembly_hours,
                        'description': "Subtarea de montaje.",
                    }
                    self.env['project.task'].create(assembly_subtask_values)

                # --- Lógica para sumar las horas al total del PROYECTO (no cambia) ---
                total_manufacturing_hours += line.manufacturing_hours
                total_assembly_hours += line.assembly_hours
                # AÑADIMOS: Acumulamos el total de horas asignadas en cada línea.
                total_allocated_hours += line.manufacturing_hours + line.assembly_hours

            # 3. Al final, actualizamos el proyecto con la suma total de horas.
            # (Simplificamos la condición para que se ejecute si hay CUALQUIER hora que sumar)
            if total_allocated_hours > 0:
                current_manufacturing = order.project_id.manufacturing_hours
                current_assembly = order.project_id.assembly_hours
                # AÑADIMOS: Obtenemos el valor actual de las horas asignadas en el proyecto.
                current_allocated = order.project_id.allocated_hours

                order.project_id.write({
                    'manufacturing_hours': current_manufacturing + total_manufacturing_hours,
                    'assembly_hours': current_assembly + total_assembly_hours,
                    'partner_id': order.partner_id.id,
                    # AÑADIMOS: Sumamos el total acumulado al valor que ya tenía el proyecto.
                    'allocated_hours': current_allocated + total_allocated_hours,
                })

        return res