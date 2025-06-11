/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.AttendancePortalWidget = publicWidget.Widget.extend({
    selector: '#attendance_portal_widget',
    events: {
        'click .btn-clock-in': '_onClickClock',
        'click .btn-clock-out': '_onClickClock',
    },

    async _onClickClock(ev) {
        ev.preventDefault();
        this.el.querySelectorAll('.btn-clock-in, .btn-clock-out').forEach(btn => btn.disabled = true);

        try {
            const result = await rpc('/my/attendance/clock', {});

            if (result.error) {
                this.el.insertAdjacentHTML('afterbegin', `<div class="alert alert-danger" role="alert">${result.error}</div>`);
            } else {
                // Mostrar mensaje de éxito temporal
                this.el.insertAdjacentHTML('afterbegin',
                    `<div class="alert alert-success" role="alert">
                        Registro de ${result.action === 'check_in' ? 'ENTRADA' : 'SALIDA'} exitoso
                    </div>`);
            }
            // Recargar después de 1.5 segundos para ver el mensaje
            setTimeout(() => window.location.reload(), 1500);

        } catch (error) {
            this.el.insertAdjacentHTML('afterbegin', `<div class="alert alert-danger" role="alert">Error de conexión</div>`);
            this.el.querySelectorAll('.btn-clock-in, .btn-clock-out').forEach(btn => btn.disabled = false);
        }
    },
});

export default publicWidget.registry.AttendancePortalWidget;