# -*- coding: utf-8 -*-

from . import models
from . import sale_order_line
from . import project_sale


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