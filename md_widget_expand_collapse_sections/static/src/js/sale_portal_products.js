/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.salePortalProducts = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'change .select_line_type': '_onDisplayTypeChanged',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onDisplayTypeChanged();
    },

    _onDisplayTypeChanged: function(ev){
        let displayType = $('select#d_line_type option:selected').val()
        if(!displayType){
            displayType =  'heads'
        }
        $('.sale_tbody tr').each(function() {
            if(!$(this).hasClass('is-subtotal') && !$(this).hasClass('o_line_section')){
                if(displayType == "heads"){
                    $(this).addClass('d-none');
                }
                else{
                    $(this).removeClass('d-none');
                }
            }
        });

    },

});
