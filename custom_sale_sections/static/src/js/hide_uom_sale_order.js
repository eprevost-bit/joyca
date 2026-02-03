/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {

    /**
     * Método correcto en Odoo 18 Enterprise
     * (NO tocar el getter `columns`)
     */
    getColumns() {

        const columns = super.getColumns();

      l
        const model = this.props?.list?.resModel;


        if (model === "sale.order.line") {
            return columns.filter(col => col.name !== "product_uom");
        }


        return columns;
    },

});
