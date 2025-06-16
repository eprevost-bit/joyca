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
                this.el.insertAdjacentHTML('afterbegin',
                    `<div class="alert alert-success" role="alert">
                        Registro de ${result.action === 'check_in' ? 'ENTRADA' : 'SALIDA'} exitoso
                    </div>`);
            }
            setTimeout(() => window.location.reload(), 1500);

        } catch (error) {
            this.el.insertAdjacentHTML('afterbegin', `<div class="alert alert-danger" role="alert">Error de conexión</div>`);
            this.el.querySelectorAll('.btn-clock-in, .btn-clock-out').forEach(btn => btn.disabled = false);
        }
    },
});

publicWidget.registry.AttendancePortalWidget.include({
    events: {
        ...publicWidget.registry.AttendancePortalWidget.prototype.events,
        'click .btn-save': '_onSaveChanges',
    },

    async _onSaveChanges(ev) {
        const btn = ev.currentTarget;
        const attendanceId = parseInt(btn.dataset.id);
        const row = btn.closest('tr');

        const checkInInput = row.querySelector('input[data-field="check_in"]');
        const checkOutInput = row.querySelector('input[data-field="check_out"]');

        // Obtener valores y validar formato HH:MM
        const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/; // Formato HH:MM

        const checkIn = checkInInput.value;
        if (!timeRegex.test(checkIn)) {
            this.displayAlert('danger', 'Formato de hora de entrada inválido. Use HH:MM');
            return;
        }

        let checkOut = null;
        if (checkOutInput && checkOutInput.value) {
            checkOut = checkOutInput.value;
            if (!timeRegex.test(checkOut)) {
                this.displayAlert('danger', 'Formato de hora de salida inválido. Use HH:MM');
                return;
            }
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';

        try {
            const result = await rpc('/my/attendance/update', {
                attendance_id: attendanceId,
                new_check_in: checkIn,
                new_check_out: checkOut,
            });

            if (result.error) {
                this.displayAlert('danger', result.error);
            } else {
                this.displayAlert('success', 'Registro actualizado correctamente');
                const durationCell = row.querySelector('td:nth-child(4)');
                if (durationCell) {
                    durationCell.textContent = result.worked_hours.toFixed(2) + ' h';
                }
            }
        } catch (error) {
            this.displayAlert('danger', 'Error al conectar con el servidor');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-save"></i> Guardar';
        }
    },

    displayAlert(type, message) {
        // Limpiar alertas anteriores
        const existingAlerts = this.el.querySelectorAll('.alert.alert-dynamic');
        existingAlerts.forEach(alert => alert.remove());

        const alert = document.createElement('div');
        alert.className = `alert alert-${type} mt-2 alert-dynamic`;
        alert.role = 'alert';
        alert.innerHTML = message;

        const container = this.el.querySelector('#editable-attendances');
        if (container) {
            container.parentNode.insertBefore(alert, container);
        } else {
            this.el.insertAdjacentElement('afterbegin', alert);
        }

        setTimeout(() => alert.remove(), 5000);
    }
});

export default publicWidget.registry.AttendancePortalWidget;
// /** @odoo-module **/
//
// import publicWidget from "@web/legacy/js/public/public_widget";
// import { rpc } from "@web/core/network/rpc";
//
// publicWidget.registry.AttendancePortalWidget = publicWidget.Widget.extend({
//     selector: '#attendance_portal_widget',
//     events: {
//         'click .btn-clock-in': '_onClickClock',
//         'click .btn-clock-out': '_onClickClock',
//     },
//
//     async _onClickClock(ev) {
//         ev.preventDefault();
//         this.el.querySelectorAll('.btn-clock-in, .btn-clock-out').forEach(btn => btn.disabled = true);
//
//         try {
//             const result = await rpc('/my/attendance/clock', {});
//
//             if (result.error) {
//                 this.el.insertAdjacentHTML('afterbegin', `<div class="alert alert-danger" role="alert">${result.error}</div>`);
//             } else {
//                 this.el.insertAdjacentHTML('afterbegin',
//                     `<div class="alert alert-success" role="alert">
//                         Registro de ${result.action === 'check_in' ? 'ENTRADA' : 'SALIDA'} exitoso
//                     </div>`);
//             }
//             setTimeout(() => window.location.reload(), 1500);
//
//         } catch (error) {
//             this.el.insertAdjacentHTML('afterbegin', `<div class="alert alert-danger" role="alert">Error de conexión</div>`);
//             this.el.querySelectorAll('.btn-clock-in, .btn-clock-out').forEach(btn => btn.disabled = false);
//         }
//     },
// });
//
// publicWidget.registry.AttendancePortalWidget.include({
//     events: {
//         ...publicWidget.registry.AttendancePortalWidget.prototype.events,
//         'click .btn-save': '_onSaveChanges',
//     },
//
//     _onSaveChanges: function(ev) {
//         const btn = ev.currentTarget;
//         const attendanceId = parseInt(btn.dataset.id);
//         const row = btn.closest('tr');
//
//         const checkInInput = row.querySelector('input[data-field="check_in"]');
//         const checkOutInput = row.querySelector('input[data-field="check_out"]');
//
//         const checkIn = checkInInput.value;
//         const checkOut = checkOutInput ? checkOutInput.value : null;
//
//         btn.disabled = true;
//         btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';
//
//         this._rpc({
//             route: '/my/attendance/update',
//             params: {
//                 attendance_id: attendanceId,
//                 new_check_in: checkIn,
//                 new_check_out: checkOut,
//             },
//         }).then((result) => {
//             if (result.error) {
//                 this.displayAlert('danger', result.error);
//             } else {
//                 this.displayAlert('success', 'Registro actualizado correctamente');
//                 const durationCell = row.querySelector('td:nth-child(4)');
//                 durationCell.textContent = result.worked_hours.toFixed(2) + ' h';
//             }
//         }).finally(() => {
//             btn.disabled = false;
//             btn.innerHTML = '<i class="fa fa-save"></i> Guardar';
//         });
//     },
//
//     displayAlert: function(type, message) {
//         const alert = document.createElement('div');
//         alert.className = `alert alert-${type} mt-2`;
//         alert.role = 'alert';
//         alert.innerHTML = message;
//
//         const container = this.el.querySelector('#editable-attendances');
//         container.parentNode.insertBefore(alert, container);
//
//         setTimeout(() => alert.remove(), 5000);
//     }
// });
//
// export default publicWidget.registry.AttendancePortalWidget;