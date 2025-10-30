/** @odoo-module **/
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import {
    SectionAndNoteListRenderer,
    SectionAndNoteFieldOne2Many,
    sectionAndNoteFieldOne2Many,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class ExpandListRenderer extends SectionAndNoteListRenderer {
    setup() {
        super.setup();
    }
    getRowClass(record) {
        const existingClasses = super.getRowClass(record);
        return `${existingClasses} o_is_${record.data.display_type}`;
    }

    getSectionColumns(columns) {
        const sectionCols = super.getSectionColumns(columns);
        return sectionCols.map((col) => {
            if (col.name === this.titleField) {
                return { ...col, colspan: columns.length - sectionCols.length+1};
            } else {
                return { ...col };
            }
        });
    }


     async onClickExpandCollapse(ev,record) {
            var currentButton = document.activeElement
            if(currentButton.classList.contains('fa-chevron-up')){
                currentButton.classList.remove('fa-chevron-up');
                currentButton.classList.add('fa-chevron-down');
             }
            else{
            currentButton.classList.remove('fa-chevron-down');
            currentButton.classList.add('fa-chevron-up');
            }
            debugger;
            var index = currentButton.closest('td').parentElement.rowIndex;
            if(!index){
                index = 0;
            }
            else{
                index = parseInt(index)
            }
            debugger;
            const t_rows = currentButton.closest('tbody').children
            for (var i = index ; i < t_rows.length; i++) {
                const row = t_rows[i];
                if(row.classList.contains('o_is_false')){
                    if(row.classList.contains('d-none')){
                        row.classList.remove('d-none');
                    }
                    else{
                        row.classList.add('d-none');
                    }
                }
                else{
                    return false
                }
            }
        }
    }





ExpandListRenderer.recordRowTemplate = "md_widget_expand_collapse_sections.ExpandListRenderer.RecordRow";
ExpandListRenderer.template = 'md_widget_expand_collapse_sections.ListRenderer';



export class SectionAndNoteFieldOne2ManyExpand extends SectionAndNoteFieldOne2Many {}
SectionAndNoteFieldOne2ManyExpand.components = {
    ...SectionAndNoteFieldOne2Many.components,
    ListRenderer: ExpandListRenderer,
};

export const sectionAndNoteFieldOne2ManyExpand = {
    ...sectionAndNoteFieldOne2Many,
    component: SectionAndNoteFieldOne2ManyExpand,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many_expand"],
};



//SectisonAndNoteFieldOne2ManyExpand
registry.category("fields").add("section_and_note_one2many_expand", sectionAndNoteFieldOne2ManyExpand );