import { SaleOrderLineProductField } from "@sale/js/sale_product_field";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup(...arguments);

        this.state = useState({
            count_item_under_section: 0,
        });
    },

    async countItemUnderSection () {
        await this.env.bus.trigger("count_item_under_section", {
            state: this.state,
            record: this.props.record
        });
    },
});
