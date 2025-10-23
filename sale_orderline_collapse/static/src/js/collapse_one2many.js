/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onMounted, onPatched } from "@odoo/owl";

/**
 * Este patch agrega comportamiento de colapsar/expandir a las secciones
 * dentro de las líneas de pedido de venta.
 */
patch(ListRenderer.prototype, {
    setup() {
        super.setup();

        const attachSectionCollapse = () => {
            const root = this.el;
            if (!root) return;

            // Solo aplica si estamos dentro de sale.order.order_line
            if (!root.closest(".o_sale_order_lines")) return;

            const rows = root.querySelectorAll("tr.o_data_row");
            rows.forEach((row, idx) => {
                const isSection = row.querySelector('[name="display_type"] input')?.value === "line_section";
                if (isSection) {
                    // Prevenir duplicado de listener
                    if (row.dataset.bound === "1") return;
                    row.dataset.bound = "1";

                    row.style.cursor = "pointer";
                    row.addEventListener("click", () => {
                        let count = 0;
                        let next = row.nextElementSibling;

                        // Ocultar/mostrar hasta la próxima sección
                        const hidden = next && next.style.display === "none" ? false : true;
                        while (next && !next.querySelector('[name="display_type"] input[value="line_section"]')) {
                            if (hidden) next.style.display = "none";
                            else next.style.display = "";
                            if (next.querySelector('[name="display_type"] input[value="line_note"]') === null)
                                count++;
                            next = next.nextElementSibling;
                        }

                        // Actualizar texto con conteo
                        const labelCell = row.querySelector('[name="name"] input, [name="name"] textarea');
                        if (labelCell) {
                            let base = labelCell.value.split('(')[0].trim();
                            if (hidden) {
                                labelCell.value = `${base} (${count})`;
                            } else {
                                labelCell.value = base;
                            }
                        }
                    });
                }
            });
        };

        // Ejecutar después de renderizar o re-renderizar
        onMounted(attachSectionCollapse);
        onPatched(attachSectionCollapse);
    },
});
