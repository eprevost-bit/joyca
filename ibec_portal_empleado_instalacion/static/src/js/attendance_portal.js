/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";


// WIDGET 1: SOLO PARA LA TARJETA DE FICHAJE EN LA PÁGINA DE INICIO (/my/home)

publicWidget.registry.AttendanceHomeWidget = publicWidget.Widget.extend({
    selector: '#attendance_portal_widget_home',
    events: {
        'click .btn-clock-in': '_onClickClock',
        'click .btn-clock-out': '_onClickClock',
    },

    start() {
        this._super.apply(this, arguments);
        const notice = localStorage.getItem('attendance_entry_notice');
        if (notice) {
            this._displayAlert('warning', 'Oye, recuerda que tu jornada laboral es de 8 horas. Si necesitas trabajar más de este tiempo, contacta con tu jefe directo y no olvides registrar tu salida.');
            localStorage.removeItem('attendance_entry_notice');
        }
    },

    async _onClickClock(ev) {
        ev.preventDefault();

        const btn = ev.currentTarget;
        btn.disabled = true;

        try {
            const result = await rpc('/my/attendance/clock', {});
            console.log("Respuesta del servidor:", result);

            if (result.error) {
                this._displayAlert('warning', result.error);
                btn.disabled = false;
                return;
            }

            this._displayAlert(
                'success',
                result.action === 'check_in'
                    ? 'Entrada registrada correctamente.'
                    : 'Salida registrada correctamente.'
            );

            setTimeout(() => {
                window.location.reload();
            }, 1200);

        } catch (error) {
            this._displayAlert('danger', 'Error de conexión con el servidor.');
            btn.disabled = false;
        }
    }
    ,

    _updateAttendanceUI(data) {
        const messageEl = this.el.querySelector('#attendance_message');
        const timeInfoEl = this.el.querySelector('#attendance_time_info');
        const statusBadge = this.el.querySelector('#attendance_status_badge');

        if (!messageEl || !timeInfoEl || !statusBadge) {
            return;
        }

        if (data.action === 'check_in') {
            messageEl.innerHTML = `Bienvenido, ${data.employee_name}`;
            timeInfoEl.textContent = `Tu entrada fue registrada a las ${data.formatted_time}.`;
            statusBadge.textContent = 'DENTRO';
            statusBadge.classList.remove('bg-danger');
            statusBadge.classList.add('bg-success');
            this._updateButtonsState('checked_in');
        } else if (data.action === 'check_out') {
            messageEl.innerHTML = `¡Hasta luego, ${data.employee_name}!`;
            let timeMessage = `Tu salida fue registrada a las ${data.formatted_time}.`;
            if (data.worked_hours !== undefined && data.worked_hours > 0) {
                const hours = data.worked_hours.toFixed(2);
                timeMessage += ` Duración total: ${hours} horas.`;
            }
            timeInfoEl.textContent = timeMessage;
            statusBadge.textContent = 'FUERA';
            statusBadge.classList.remove('bg-success');
            statusBadge.classList.add('bg-danger');
            this._updateButtonsState('checked_out');
        }
        const actionText = data.action === 'check_in' ? 'ENTRADA' : 'SALIDA';
        this._displayAlert('success', `Registro de ${actionText} exitoso.`);
    },

    /*_updateButtonsState(state) {
        const btnIn = this.el.querySelector('.btn-clock-in');
        const btnOut = this.el.querySelector('.btn-clock-out');
        if (btnIn) btnIn.disabled = true;
        if (btnOut) btnOut.disabled = true;


        if (state === 'checked_in') {
            btnIn.disabled = true;
            btnOut.disabled = false;
        } else {
            btnIn.disabled = false;
            btnOut.disabled = true;
        }
    },*/

    /**
     * Muestra una alerta dentro de la tarjeta.
     */
    _displayAlert(type, message) {
        const alertContainer = this.el.querySelector('.card-header');
        if (!alertContainer) return;

        // elimina alertas previas
        const existing = this.el.querySelector('.alert');
        if (existing) existing.remove();

        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show mt-2 mb-0`;
        alert.role = 'alert';
        alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

        alertContainer.insertAdjacentElement('afterend', alert);

        setTimeout(() => alert.remove(), 5000);
    },

});


// WIDGET 2: PARA LA PÁGINA DE DETALLE DE ASISTENCIAS (/my/attendances)
// (Contiene la lógica de la tabla, borrado, modal, etc.)
publicWidget.registry.AttendancePageWidget = publicWidget.Widget.extend({
    selector: '#attendance_portal_widget',
    events: {
        'click .btn-manual-entry': '_onClickManualEntry',
        'click .btn-clock-in': '_onClickClock',
        'click .btn-clock-out': '_onClickClock',
        'click .btn-save': '_onSaveChanges',
        'click .btn-delete': '_onDeleteAttendance',
        'click .page-link': '_onPageClick',
        'shown.bs.modal #manualEntryModal': '_onManualIntervalModalShown',
        'click #add-interval-btn': '_onAddInterval',
        'click .btn-remove-interval': '_onRemoveInterval',
        'click #btn-save-manual-intervals': '_onSaveManualIntervals',
    },


    start() {
        this._super.apply(this, arguments);
        $(this.el).find('[data-bs-toggle="tooltip"]').tooltip({trigger: 'hover', placement: 'top'});
    },
    _displayButtonAlert(btn, type, message) {

        const existing = btn.parentElement.querySelector('.alert');
        if (existing) {
            existing.remove();
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${type} mt-2 mb-2`;
        alert.role = 'alert';
        alert.textContent = message;


        btn.parentElement.insertBefore(alert, btn);

        if (type !== 'success') {
            setTimeout(() => alert.remove(), 5000);
        }
    },

    async _onClickClock(ev) {
        ev.preventDefault();

        const btn = ev.currentTarget;
        btn.disabled = true;

        try {
            const result = await rpc('/my/attendance/clock', {});
            console.log("Respuesta del servidor:", result);

            if (result.error) {
                this._displayAlert('warning', result.error);
                btn.disabled = false;
                return;
            }

            this._displayAlert(
                'success',
                result.action === 'check_in'
                    ? 'Entrada registrada correctamente.'
                    : 'Salida registrada correctamente.'
            );

            setTimeout(() => {
                window.location.reload();
            }, 1200);

        } catch (error) {
            this._displayAlert('danger', 'Error de conexión con el servidor.');
            btn.disabled = false;
        }
    },

    _onClickManualEntry(ev) {
        const btn = ev.currentTarget;
        const hasOpenAttendance = btn.dataset.hasOpenAttendance === 'True';

        if (hasOpenAttendance) {
            ev.preventDefault();
            ev.stopImmediatePropagation();

            this._displayButtonAlert(
                btn,
                'warning',
                '⚠️ No puedes registrar un día completo porque tienes una jornada abierta. Registra primero la SALIDA.'
            );


            return;
        }


        const modal = this.el.querySelector('#manualEntryModal');
        if (modal) {
            $(modal).modal('show');
        }
    }
    ,


    _onPageClick(ev) {
        ev.preventDefault();
        window.location.href = ev.currentTarget.getAttribute('href');
    },

    async _onSaveChanges(ev) {
        const btn = ev.currentTarget;
        const attendanceId = parseInt(btn.dataset.id);
        const row = btn.closest('tr');
        if (!row) return;

        const dateInput = row.querySelector('input[data-field="check_in_date"]');
        const checkInInput = row.querySelector('input[data-field="check_in"]');
        const checkOutInput = row.querySelector('input[data-field="check_out"]');

        const dateValue = dateInput.value;
        const checkIn = checkInInput.value;
        let checkOut = null;
        if (checkOutInput && checkOutInput.value) {
            checkOut = checkOutInput.value;
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';
        try {
            const result = await rpc('/my/attendance/update', {
                attendance_id: attendanceId,
                new_check_in_date: dateValue,
                new_check_in: checkIn,
                new_check_out: checkOut,
            });
            if (result.error) {
                this._displayAlert('danger', result.error);
            } else {
                this._displayAlert('success', 'Registro actualizado correctamente');
                const durationCell = row.querySelector('td:nth-of-type(4)');
                if (durationCell && result.worked_hours !== undefined) {
                    durationCell.textContent = `${result.worked_hours.toFixed(2)} h`;
                }
            }
        } catch (error) {
            this._displayAlert('danger', 'Error al conectar con el servidor');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-save"></i> Guardar';
        }
    },

    async _onDeleteAttendance(ev) {
        ev.preventDefault();
        const btn = ev.currentTarget;
        const attendanceId = parseInt(btn.dataset.id);
        const row = btn.closest('tr');
        if (!confirm('¿Estás seguro de que quieres eliminar este registro?')) {
            return;
        }
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Eliminando...';
        try {
            const result = await rpc('/my/attendance/delete', {
                attendance_id: attendanceId,
            });
            if (result.error) {
                this._displayAlert('danger', result.error);
            } else {
                this._displayAlert('success', result.message || 'Registro eliminado correctamente');
                row.remove();
            }
        } catch (error) {
            this._displayAlert('danger', 'Error al conectar con el servidor');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-trash"></i> Eliminar';
        }
    },

    _onManualIntervalModalShown: function () {

        const container = this.el.querySelector('#time-intervals-container');
        container.innerHTML = `
            <div class="row g-3 align-items-center mb-2 time-interval-row">
                <div class="col-auto"><label class="col-form-label">De:</label></div>
                <div class="col"><input type="time" class="form-control manual-check-in" required="1"/></div>
                <div class="col-auto"><label class="col-form-label">A:</label></div>
                <div class="col"><input type="time" class="form-control manual-check-out" required="1"/></div>
                <div class="col-auto">
                    <button type="button" class="btn btn-danger btn-sm btn-remove-interval" title="Eliminar horario" style="display: none;">
                        <i class="fa fa-trash"/>
                    </button>
                </div>
            </div>`;
        const dateInput = this.el.querySelector('#manualEntryDate');
        if (dateInput) {
            const today = new Date().toISOString().split('T')[0];
            dateInput.value = today;
            dateInput.max = today;
        }
    },

    _onAddInterval: function () {
        const container = this.el.querySelector('#time-intervals-container');
        const firstRow = container.querySelector('.time-interval-row');
        const newRow = firstRow.cloneNode(true);
        newRow.querySelector('.manual-check-in').value = '';
        newRow.querySelector('.manual-check-out').value = '';
        newRow.querySelector('.btn-remove-interval').style.display = 'inline-block';
        container.appendChild(newRow);
    },

    _onRemoveInterval: function (ev) {
        ev.currentTarget.closest('.time-interval-row').remove();
    },

    async _onSaveManualIntervals(ev) {
        const btn = ev.currentTarget;

        const hasOpenAttendance = this.el.querySelector('.btn-manual-entry')
            ?.dataset.hasOpenAttendance === 'True';

        if (hasOpenAttendance) {
            this._displayButtonAlert(
                btn,
                'warning',
                'No puedes registrar un día completo mientras tengas una jornada abierta.'
            );
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';

        const modalBodySelector = '#manualEntryModal .modal-body';
        const date = this.el.querySelector('#manualEntryDate').value;

        if (!date) {
            this._displayAlert('danger', 'Selecciona una fecha.', modalBodySelector);
            btn.disabled = false;
            btn.innerHTML = 'Guardar Horarios';
            return;
        }

        const intervals = [];
        const rows = this.el.querySelectorAll('.time-interval-row');

        for (const row of rows) {
            const checkIn = row.querySelector('.manual-check-in').value;
            const checkOut = row.querySelector('.manual-check-out').value;

            if (checkIn && checkOut) {
                intervals.push({check_in: checkIn, check_out: checkOut});
            }
        }

        if (!intervals.length) {
            this._displayAlert('warning', 'Introduce al menos un horario válido.', modalBodySelector);
            btn.disabled = false;
            btn.innerHTML = 'Guardar Horarios';
            return;
        }

        intervals.sort((a, b) => a.check_in.localeCompare(b.check_in));

        for (let i = 0; i < intervals.length; i++) {
            const {check_in, check_out} = intervals[i];

            if (check_in >= check_out) {
                this._displayAlert(
                    'danger',
                    'La hora de entrada debe ser menor que la de salida.',
                    modalBodySelector
                );
                btn.disabled = false;
                btn.innerHTML = 'Guardar Horarios';
                return;
            }

            if (i > 0 && intervals[i - 1].check_out > check_in) {
                this._displayAlert(
                    'danger',
                    'Los horarios no pueden solaparse.',
                    modalBodySelector
                );
                btn.disabled = false;
                btn.innerHTML = 'Guardar Horarios';
                return;
            }
        }

        try {
            const result = await rpc('/my/attendance/manual_entry_intervals', {
                date,
                intervals,
            });

            if (result.error) {
                this._displayAlert('danger', result.error, modalBodySelector);
                btn.disabled = false;
                btn.innerHTML = 'Guardar Horarios';
                return;
            }

            this._displayButtonAlert(
                btn,
                'success',
                result.message || 'Horarios guardados correctamente.'
            );

            setTimeout(() => {
                const modalEl = this.el.querySelector('#manualEntryModal');
                if (modalEl) {
                    $(modalEl).modal('hide');
                }
                window.location.reload();
            }, 1500);

        } catch (error) {
            this._displayAlert('danger', 'Error de conexión con el servidor.', modalBodySelector);
            btn.disabled = false;
            btn.innerHTML = 'Guardar Horarios';
        }
    },


    /**
     * Muestra una alerta en la interfaz. Acepta un 'target' opcional
     * para mostrar la alerta dentro de un elemento específico (ej. un modal).
     */
    _displayAlert(type, message, target = false) {
        const container = target ? this.el.querySelector(target) : this.el;
        if (!container) {
            console.error("Contenedor de alerta no encontrado:", target || this.selector);
            return;
        }

        const existingAlert = container.querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.role = 'alert';
        alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;

        container.prepend(alert); // La pone al principio del contenedor

        // Las alertas de error o aviso se auto-eliminan. La de éxito no, porque la página se recargará.
        if (type !== 'success') {
            setTimeout(() => alert.remove(), 5000);
        }
    },
});
// =================================================================
// publicWidget.registry.AttendancePageWidget = publicWidget.Widget.extend({
//     selector: '#attendance_portal_widget',
//     events: {
//         'click .btn-save': '_onSaveChanges',
//         'click .btn-delete': '_onDeleteAttendance',
//         'click .page-link': '_onPageClick',
//         'shown.bs.modal #manualEntryModal': '_onManualIntervalModalShown',
//         'click #add-interval-btn': '_onAddInterval',
//         'click .btn-remove-interval': '_onRemoveInterval',
//         'click #btn-save-manual-intervals': '_onSaveManualIntervals',
//     },
//
//     start() {
//         this._super.apply(this, arguments);
//         $(this.el).find('[data-bs-toggle="tooltip"]').tooltip({trigger: 'hover', placement: 'top'});
//     },
//
//     _onPageClick(ev) {
//         ev.preventDefault();
//         window.location.href = ev.currentTarget.getAttribute('href');
//     },
//
//     async _onSaveChanges(ev) {
//         const btn = ev.currentTarget;
//         const attendanceId = parseInt(btn.dataset.id);
//         const row = btn.closest('tr');
//         if (!row) return;
//
//         const dateInput = row.querySelector('input[data-field="check_in_date"]');
//         const checkInInput = row.querySelector('input[data-field="check_in"]');
//         const checkOutInput = row.querySelector('input[data-field="check_out"]');
//
//         const dateValue = dateInput.value;
//         const checkIn = checkInInput.value;
//         let checkOut = null;
//         if (checkOutInput && checkOutInput.value) {
//             checkOut = checkOutInput.value;
//         }
//
//         btn.disabled = true;
//         btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';
//         try {
//             const result = await rpc('/my/attendance/update', {
//                 attendance_id: attendanceId,
//                 new_check_in_date: dateValue,
//                 new_check_in: checkIn,
//                 new_check_out: checkOut,
//             });
//             if (result.error) {
//                 this._displayAlert('danger', result.error);
//             } else {
//                 this._displayAlert('success', 'Registro actualizado correctamente');
//                 const durationCell = row.querySelector('td:nth-of-type(4)');
//                 if (durationCell && result.worked_hours !== undefined) {
//                     durationCell.textContent = `${result.worked_hours.toFixed(2)} h`;
//                 }
//             }
//         } catch (error) {
//             this._displayAlert('danger', 'Error al conectar con el servidor');
//         } finally {
//             btn.disabled = false;
//             btn.innerHTML = '<i class="fa fa-save"></i> Guardar';
//         }
//     },
//
//     async _onDeleteAttendance(ev) {
//         ev.preventDefault();
//         const btn = ev.currentTarget;
//         const attendanceId = parseInt(btn.dataset.id);
//         const row = btn.closest('tr');
//         if (!confirm('¿Estás seguro de que quieres eliminar este registro?')) {
//             return;
//         }
//         btn.disabled = true;
//         btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Eliminando...';
//         try {
//             const result = await rpc('/my/attendance/delete', {
//                 attendance_id: attendanceId,
//             });
//             if (result.error) {
//                 this._displayAlert('danger', result.error);
//             } else {
//                 this._displayAlert('success', result.message || 'Registro eliminado correctamente');
//                 row.remove();
//             }
//         } catch (error) {
//             this._displayAlert('danger', 'Error al conectar con el servidor');
//         } finally {
//             btn.disabled = false;
//             btn.innerHTML = '<i class="fa fa-trash"></i> Eliminar';
//         }
//     },
//
//     _onManualIntervalModalShown: function () {
//         const container = this.el.querySelector('#time-intervals-container');
//         container.innerHTML = `
//             <div class="row g-3 align-items-center mb-2 time-interval-row">
//                 <div class="col-auto"><label class="col-form-label">De:</label></div>
//                 <div class="col"><input type="time" class="form-control manual-check-in" required="1"/></div>
//                 <div class="col-auto"><label class="col-form-label">A:</label></div>
//                 <div class="col"><input type="time" class="form-control manual-check-out" required="1"/></div>
//                 <div class="col-auto">
//                     <button type="button" class="btn btn-danger btn-sm btn-remove-interval" title="Eliminar horario" style="display: none;">
//                         <i class="fa fa-trash"/>
//                     </button>
//                 </div>
//             </div>`;
//         const dateInput = this.el.querySelector('#manualEntryDate');
//         if (dateInput) {
//             const today = new Date().toISOString().split('T')[0];
//             dateInput.value = today;
//             dateInput.max = today;
//         }
//     },
//
//     _onAddInterval: function () {
//         const container = this.el.querySelector('#time-intervals-container');
//         const firstRow = container.querySelector('.time-interval-row');
//         const newRow = firstRow.cloneNode(true);
//         newRow.querySelector('.manual-check-in').value = '';
//         newRow.querySelector('.manual-check-out').value = '';
//         newRow.querySelector('.btn-remove-interval').style.display = 'inline-block';
//         container.appendChild(newRow);
//     },
//
//     _onRemoveInterval: function (ev) {
//         ev.currentTarget.closest('.time-interval-row').remove();
//     },
//
//     async _onSaveManualIntervals(ev) {
//         const btn = ev.currentTarget;
//         btn.disabled = true;
//         btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';
//
//         const date = this.el.querySelector('#manualEntryDate').value;
//         if (!date) {
//             this._displayAlert('danger', 'Por favor, selecciona una fecha.');
//             btn.disabled = false;
//             btn.innerHTML = 'Guardar Horarios';
//             return;
//         }
//
//         const intervals = [];
//         const rows = this.el.querySelectorAll('.time-interval-row');
//         let isValid = true;
//         rows.forEach(row => {
//             const checkIn = row.querySelector('.manual-check-in').value;
//             const checkOut = row.querySelector('.manual-check-out').value;
//             if (checkIn && checkOut) {
//                 if (checkIn >= checkOut) {
//                     this._displayAlert('danger', `La hora de entrada (${checkIn}) debe ser menor que la de salida (${checkOut}).`);
//                     isValid = false;
//                 }
//                 intervals.push({check_in: checkIn, check_out: checkOut});
//             }
//         });
//
//         if (!isValid || intervals.length === 0) {
//             if (intervals.length === 0) {
//                 this._displayAlert('warning', 'No has introducido ningún horario válido para guardar.');
//             }
//             btn.disabled = false;
//             btn.innerHTML = 'Guardar Horarios';
//             return;
//         }
//
//         try {
//             const result = await rpc('/my/attendance/manual_entry_intervals', {date: date, intervals: intervals});
//
//             if (result.error) {
//                 this._displayAlert('danger', result.error);
//             } else {
//                 // ¡ÉXITO!
//                 this._displayAlert('success', result.message || 'Horarios guardados correctamente.');
//
//                 // === INICIO DE LA CORRECCIÓN ===
//                 // Buscamos el modal
//                 const modalEl = this.el.querySelector('#manualEntryModal');
//                 if (modalEl) {
//                     $(modalEl).modal('hide');
//                 }
//
//                 // Planificamos la recarga de la página para ver el nuevo registro.
//                 setTimeout(() => {
//                     window.location.reload();
//                 }, 1500); // 1.5 segundos de espera para que el usuario vea el mensaje de éxito.
//                 // === FIN DE LA CORRECCIÓN ===
//             }
//         } catch (error) {
//             // Este bloque ya no debería ejecutarse si la conexión es buena.
//             this._displayAlert('danger', 'Error de conexión con el servidor.');
//         } finally {
//             // Este bloque se ejecuta siempre, pero como la página se va a recargar,
//             // no es crítico restaurar el botón.
//             btn.disabled = false;
//             btn.innerHTML = 'Guardar Horarios';
//         }
//     },
//
//     _displayAlert(type, message) {
//         const container = this.el;
//         const alert = document.createElement('div');
//         alert.className = `alert alert-${type} alert-dismissible fade show mt-2`;
//         alert.role = 'alert';
//         alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
//         container.prepend(alert);
//         setTimeout(() => alert.remove(), 5000);
//     },
// });
