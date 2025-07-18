/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component, onWillUpdateProps, useState } = owl;

class SectionPagerWidget extends Component {
    static template = "custom_sale_sections.SectionPagerWidget";
    static components = { X2ManyField };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({
            currentPage: 0,
            sections: [],
        });

        onWillUpdateProps((nextProps) => {
            this._prepareSections(nextProps.record.data.order_line);
        });

        this._prepareSections(this.props.record.data.order_line);
    }

    _prepareSections(lineList) {
        const lines = lineList.records;
        if (!lines || lines.length === 0) {
            this.state.sections = [];
            return;
        }

        const sections = [];
        let currentSection = null;

        for (const line of lines) {
            if (line.data.display_type === 'line_section') {
                if (currentSection) {
                    sections.push(currentSection);
                }
                currentSection = {
                    header: line,
                    lines: [],
                    name: line.data.name,
                };
            } else if (currentSection) {
                // Modificación: Agregamos también las notas a la sección para que no se pierdan
                 if(line.data.display_type === 'line_note' || !line.data.display_type) {
                    currentSection.lines.push(line);
                 }
            }
        }
        if (currentSection) {
            sections.push(currentSection);
        }
        this.state.sections = sections;
         // Si solo hay una sección, nos aseguramos de que la página sea la 0
        if (this.state.sections.length === 1) {
            this.state.currentPage = 0;
        }
    }

    _onNextPage() {
        if (this.state.currentPage < this.state.sections.length - 1) {
            this.state.currentPage++;
        }
    }

    _onPrevPage() {
        if (this.state.currentPage > 0) {
            this.state.currentPage--;
        }
    }

    // --- Propiedades para la vista de líneas (VERSIÓN CORREGIDA) ---
    get currentLines() {
        if (!this.state.sections.length) {
            return { ...this.props.record.data.order_line, records: [] };
        }

        const currentSection = this.state.sections[this.state.currentPage];
        if (!currentSection) {
            return { ...this.props.record.data.order_line, records: [] };
        }

        const recordsToShow = [currentSection.header, ...currentSection.lines];

        return {
            ...this.props.record.data.order_line,
            records: recordsToShow,
        };
    }
}

registry.category("fields").add("section_pager_widget", {
    component: SectionPagerWidget,
    supportedTypes: ["one2many"],
});