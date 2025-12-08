/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import {
    SectionAndNoteListRenderer,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";

import { SaleOrderLineListRenderer } from '@sale/js/sale_order_line_field/sale_order_line_field';
import { cookie } from "@web/core/browser/cookie";

import { useBus } from "@web/core/utils/hooks";

patch(SaleOrderLineListRenderer.prototype, {

    setup() {
        super.setup(...arguments);

        useBus(this.env.bus, "count_item_under_section", async (ev) => {
            let count = this.countItemUnderSection(ev.detail.record);
            ev.detail.state.count_item_under_section = count;
        });
    },

    async collapseSection(record) {
        this._collapseExpandSection (record);
    },

    titleCollapseExpand(record=null) {
        record = record || this.record;

        const startIndex = this.props.list.records.findIndex(rec => rec.id === record.id);
        let hasOrderLine = false;
        if (startIndex !== -1) {
            let recordsAfter = this.props.list.records.slice(startIndex + 1);
            if (recordsAfter.length > 0) {
                recordsAfter.every(rec => {
                    if (rec.data.display_type !== 'line_section') {
                        hasOrderLine = true;
                        return false;
                    }
                    else {
                        return false;
                    }
                });
            }
        }

        if (!hasOrderLine) {
            return "";
        }

        let is_collapse = cookie.get('section_' + record.evalContext.id);
        if (is_collapse) {
            if (this._check_is_collapse(record)) {
                return "Expand";
            }
            else {
                cookie.set('section_' + record.evalContext.id, "", -1);
                return "Collapse";
            }
        }
        else {
            return "Collapse";
        }
    },

    _check_is_collapse (record) {
        const startIndex = this.props.list.records.findIndex(rec => rec.id === record.id);
        let is_collapse = false;
        if (startIndex !== -1) {
            let recordsAfter = this.props.list.records.slice(startIndex + 1);
            if (recordsAfter.length > 0) {
                recordsAfter.every(rec => {
                    if (rec.data.display_type !== 'line_section') {
                        let belong_to_section = cookie.get('belong_to_section_' + rec.evalContext.id);
                        if (belong_to_section === record.evalContext.id.toString()) {
                            is_collapse = true;
                            return false;
                        }
                    }
                });
            }
        }
        return is_collapse;
    },

    countItemUnderSection (record) {
        const startIndex = this.props.list.records.findIndex(rec => rec.id === record.id);
        let count = 0;
        if (startIndex !== -1) {
            let recordsAfter = this.props.list.records.slice(startIndex + 1);
            if (recordsAfter.length > 0) {
                recordsAfter.every(rec => {
                    if (!rec.data.combo_item_id && ['product', 'consu', 'combo'].includes(rec.data.product_type)) {
                        count += 1;
                        return true;
                    }
                    if (rec.data.display_type === 'line_section') {
                        return false;
                    }
                    if (rec.data.display_type === 'line_note' || rec.data.display_type === 'line_subsection') {
                        return true;
                    }
                });
            }
        }
        return count;
    },

    getRowClass(record) {
        let classNames = super.getRowClass(...arguments);
        if (record.evalContext.id != false) {
            let belong_to_section = cookie.get('belong_to_section_' + record.evalContext.id);
            if (belong_to_section) {
                classNames += ' d-none';
            }
        }

        return classNames;
    },

    async _collapseExpandSection(record) {
        let is_collapse = cookie.get('section_' + record.evalContext.id);

        if (is_collapse === undefined) {
            await this._applyOrRemoveCookieSection(record, true);

            const startIndex = this.props.list.records.findIndex(rec => rec.id === record.id);
            if (startIndex !== -1) {
                let recordsAfter = this.props.list.records.slice(startIndex + 1);
                if (recordsAfter.length > 0) {
                    cookie.set('section_' + record.evalContext.id, true);
                    // After render, it will call call onInitalCollapseExpand
                    this.render();
                }
            }
        }
        else {
            await this._applyOrRemoveCookieSection(record, false);
            cookie.set('section_' + record.evalContext.id, "", -1);
            // After render, it will call call onInitalCollapseExpand
            this.render();
        }
    },

    async onDeleteRecord(record) {
         if  (record.data.display_type === 'line_section') {
             this._applyOrRemoveCookieSection(record, false);
             let is_collapse = cookie.get('section_' + record.evalContext.id);
             if (is_collapse) {
                cookie.set('section_' + record.evalContext.id, "", -1);
                // Expand when section line is deleted.
                await this._toggleCollapseExpand(record, false);
             }
         }
         else {
            cookie.set('belong_to_section_' + record.evalContext.id, "", -1);
         }
         await super.onDeleteRecord(...arguments);
    },

    _applyOrRemoveCookieSection (record, apply=true) {
        const startIndex = this.props.list.records.findIndex(rec => rec.id === record.id);
        if (startIndex !== -1) {
            let recordsAfter = this.props.list.records.slice(startIndex + 1);
            if (recordsAfter.length > 0) {
                recordsAfter.every(rec => {
                    if (rec.data.display_type !== 'line_section') {
                        if (apply) {
                            cookie.set('belong_to_section_' + rec.evalContext.id, record.evalContext.id);
                        }
                        else{
                            cookie.set('belong_to_section_' + rec.evalContext.id, "", -1);
                        }
                        return true;
                    }
                    else {
                        return false;
                    }
                });
            }
        }
    },

    _toggleCollapseExpand (record, is_collapse) {
        const startIndex = this.props.list.records.findIndex(rec => rec.id === record.id);
        if (startIndex !== -1) {
            let recordsAfter = this.props.list.records.slice(startIndex + 1);
            if (recordsAfter.length > 0) {
                recordsAfter.every(rec => {
                    if (rec.data.display_type !== 'line_section') {
                        const dynamicId = rec.id;
                        const trRow = $(`tr[data-id="${dynamicId}"]`);
                        if (is_collapse) {
                            let belong_to_section = cookie.get('belong_to_section_' + rec.evalContext.id);

                            if (belong_to_section === record.evalContext.id.toString()) {
                                trRow.addClass('d-none')
                            }
                        }
                        else {
                            trRow.removeClass('d-none');
                        }
                        return true;
                    }
                    else {
                        return false;
                    }
                });
            }
        }
    },

});
