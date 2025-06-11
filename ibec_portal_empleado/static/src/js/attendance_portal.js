/** @odoo-module **/

// Ya no necesitas importar jsonrpc directamente
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.AttendancePortalWidget = publicWidget.Widget.extend({
    selector: '#attendance_portal_widget',
    events: {
        'click .btn-clock-in': '_onClickClock',
        'click .btn-clock-out': '_onClickClock',
    },

    async _onClickClock(ev) {
        ev.preventDefault();
        this.el.querySelectorAll('.btn-clock-in, .btn-clock-out').forEach(btn => btn.disabled = true);
        const result = await this.rpc('/my/attendance/clock', {});

        if (result.error) {
            this.el.insertAdjacentHTML('afterbegin', `<div class="alert alert-danger" role="alert">${result.error}</div>`);
            // Volvemos a habilitar los botones si hay un error
            this.el.querySelectorAll('.btn-clock-in, .btn-clock-out').forEach(btn => btn.disabled = false);
        } else {
            window.location.reload();
        }
    },
});

export default publicWidget.registry.AttendancePortalWidget;