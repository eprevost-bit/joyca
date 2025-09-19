/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";

publicWidget.registry.AttendancePortalWidget = publicWidget.Widget.extend({
    selector: '#attendance_portal_widget, #attendance_portal_widget_home',
    events: {
        'click .btn-clock-in': '_onClickClock',
        'click .btn-clock-out': '_onClickClock',
        'click .btn-save': '_onSaveChanges',
        'click .btn-delete': '_onDeleteAttendance',
        'click .btn-submit-manual': '_onSubmitManualEntry',
        'shown.bs.modal #manualEntryModal': '_onManualModalShown',
        'click .page-link': '_onPageClick'
    },

    /**
     * Maneja el click en los enlaces de paginación
     */
    _onPageClick(ev) {
        ev.preventDefault();
        const url = ev.currentTarget.getAttribute('href');
        window.location.href = url;
    },

    /**
     * Maneja el evento de clic en los botones de entrada/salida
     */
    async _onClickClock(ev) {
        ev.preventDefault();
        const btn = ev.currentTarget;
        btn.disabled = true;

        try {
            const result = await rpc('/my/attendance/clock', {});

            if (result.error) {
                this._displayAlert('danger', result.error);
            } else {
                const action = result.action === 'check_in' ? 'ENTRADA' : 'SALIDA';

                this._displayAlert('success', `Registro de ${action} exitoso`);

                if (result.action === 'check_in') {
                    this._displayAlert(
                        'warning',
                        'Disfrute su tiempo de trabajo. Recuerde que debe registrar su salida al finalizar su jornada laboral.'
                    );
                }
                if (result.action === 'check_in') {
                    localStorage.setItem('attendance_entry_notice', '1');
                }
                setTimeout(() => window.location.reload(), 3500);
            }
        } catch (error) {
            this._displayAlert('danger', 'Error de conexión con el servidor');
            btn.disabled = false;
        }
    },

    /**
     * Maneja el evento de guardar cambios en los registros editables
     */
    async _onSaveChanges(ev) {
        const btn = ev.currentTarget;
        const attendanceId = parseInt(btn.dataset.id);
        const row = btn.closest('tr');

        // Si no se encuentra una fila (estamos en una página sin tabla), no hacemos nada.
        if (!row) {
            return;
        }

        const dateInput = row.querySelector('input[data-field="check_in_date"]');
        const checkInInput = row.querySelector('input[data-field="check_in"]');
        const checkOutInput = row.querySelector('input[data-field="check_out"]');

        // Validar formato de fecha YYYY-MM-DD
        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        const dateValue = dateInput.value;
        if (!dateRegex.test(dateValue)) {
            this._displayAlert('danger', 'Formato de fecha inválido. Use YYYY-MM-DD');
            return;
        }

        // Validar formato HH:MM
        const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;

        const checkIn = checkInInput.value;
        if (!timeRegex.test(checkIn)) {
            this._displayAlert('danger', 'Formato de hora de entrada inválido. Use HH:MM');
            return;
        }

        let checkOut = null;
        if (checkOutInput && checkOutInput.value) {
            checkOut = checkOutInput.value;
            if (!timeRegex.test(checkOut)) {
                this._displayAlert('danger', 'Formato de hora de salida inválido. Use HH:MM');
                return;
            }
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
                
                // --- INICIO DE LA CORRECCIÓN ---
                // Actualizar la visualización de la fecha (solo si la celda existe)
                const dateCell = row.querySelector('td:nth-child(1)');
                if (dateCell) {
                    const dateParts = dateValue.split('-');
                    dateCell.textContent = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
                }
                
                // Actualizar la duración (solo si la celda existe)
                const durationCell = row.querySelector('td:nth-child(4)');
                if (durationCell) {
                    durationCell.textContent = `${result.worked_hours.toFixed(2)} h`;
                }
                // --- FIN DE LA CORRECCIÓN ---
            }
        } catch (error) {
            this._displayAlert('danger', 'Error al conectar con el servidor');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-save"></i> Guardar';
        }
    },
    /**
     * Maneja la eliminación de un registro
     */
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
                // Eliminar la fila de la tabla
                row.remove();
            }
        } catch (error) {
            this._displayAlert('danger', 'Error al conectar con el servidor');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-trash"></i> Eliminar';
        }
    },

    /**
     * Maneja el registro manual de un día completo
     */
    async _onSubmitManualEntry(ev) {
        ev.preventDefault();
        const btn = ev.currentTarget;
        const modal = this.el.querySelector('#manualEntryModal');

        const date = this.el.querySelector('#manualEntryDate').value;
        const checkIn = this.el.querySelector('#manualCheckIn').value;
        const checkOut = this.el.querySelector('#manualCheckOut').value;

        // Validaciones
        if (!date || !checkIn || !checkOut) {
            this._displayAlert('danger', 'Todos los campos son obligatorios');
            return;
        }

        if (checkIn >= checkOut) {
            this._displayAlert('danger', 'La hora de entrada debe ser anterior a la hora de salida');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';

        try {
            const result = await rpc('/my/attendance/manual_entry', {
                date: date,
                check_in: checkIn,
                check_out: checkOut,
            });

            if (result.error) {
                this._displayAlert('danger', result.error);
            } else {
                this._displayAlert('success', result.message || 'Registro manual guardado correctamente');
                // Cerrar el modal y limpiar el formulario
                const modalInstance = bootstrap.Modal.getInstance(modal);
                modalInstance.hide();
                this._resetManualEntryForm();
                // Recargar después de 2 segundos
                setTimeout(() => window.location.reload(), 2000);
            }
        } catch (error) {
            this._displayAlert('danger', 'Error al conectar con el servidor: ' + (error.message || ''));
        } finally {
            btn.disabled = false;
            btn.innerHTML = 'Guardar';
        }
    },

    /**
     * Cuando se muestra el modal de registro manual
     */
    _onManualModalShown() {
        // Establecer la fecha por defecto a hoy
        const today = new Date().toISOString().split('T')[0];
        const dateInput = this.el.querySelector('#manualEntryDate');
        dateInput.value = today;
        dateInput.max = today;

        // Establecer horas por defecto (8:00 - 17:00)
        this.el.querySelector('#manualCheckIn').value = '08:00';
        this.el.querySelector('#manualCheckOut').value = '17:00';
    },

    /**
     * Limpia el formulario de registro manual
     */
    _resetManualEntryForm() {
        const form = this.el.querySelector('#manualEntryForm');
        if (form) {
            form.reset();
        }
    },

    /**
     * Muestra una alerta en la interfaz
     * @param {string} type - Tipo de alerta (success, danger, warning, etc.)
     * @param {string} message - Mensaje a mostrar
     */
    _displayAlert(type, message) {
        // Limpiar alertas anteriores del mismo tipo
        const existingAlerts = this.el.querySelectorAll(`.alert.alert-${type}`);
        existingAlerts.forEach(alert => alert.remove());

        const alert = document.createElement('div');
        alert.className = `alert alert-${type} mt-2 mb-3`;
        alert.role = 'alert';
        alert.innerHTML = `
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            ${message}
        `;

        // Insertar la alerta en un lugar visible
        const header = this.el.querySelector('.card-header');
        if (header) {
            header.insertAdjacentElement('afterend', alert);
        } else {
            this.el.insertAdjacentElement('afterbegin', alert);
        }

        // Configurar autodestrucción después de 5 segundos
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    },

    /**
     * Inicialización del widget
     */
    start() {
        // Configurar tooltips para los botones
        $(this.el).find('[data-bs-toggle="tooltip"]').tooltip({
            trigger: 'hover',
            placement: 'top'
        });

        const notice = localStorage.getItem('attendance_entry_notice');
        if (notice) {
            this._displayAlert(
                'warning',
                'Oye, recuerda que tu jornada laboral es de 8 horas. Si necesitas trabajar más de este tiempo, contacta con tu jefe directo y no olvides registrar tu salida.'
            );
            localStorage.removeItem('attendance_entry_notice');
        }

        return this._super.apply(this, arguments);
    }
});

export default publicWidget.registry.AttendancePortalWidget;
// /** @odoo-module **/
//
// import publicWidget from "@web/legacy/js/public/public_widget";
// import {rpc} from "@web/core/network/rpc";
//
// publicWidget.registry.AttendancePortalWidget = publicWidget.Widget.extend({
//     selector: '#attendance_portal_widget, #attendance_portal_widget_home',
//     events: {
//         'click .btn-clock-in': '_onClickClock',
//         'click .btn-clock-out': '_onClickClock',
//         'click .btn-save': '_onSaveChanges',
//         'click .btn-submit-manual': '_onSubmitManualEntry',
//         'shown.bs.modal #manualEntryModal': '_onManualModalShown',
//         'click .page-link': '_onPageClick'
//     },
//
//     _onPageClick(ev) {
//         ev.preventDefault();
//         const url = ev.currentTarget.getAttribute('href');
//         window.location.href = url;
//     },
//
//     /**
//      * Maneja el evento de clic en los botones de entrada/salida
//      */
//     async _onClickClock(ev) {
//         ev.preventDefault();
//         const btn = ev.currentTarget;
//         btn.disabled = true;
//
//         try {
//             const result = await rpc('/my/attendance/clock', {});
//
//             if (result.error) {
//                 this._displayAlert('danger', result.error);
//             } else {
//                 const action = result.action === 'check_in' ? 'ENTRADA' : 'SALIDA';
//
//                 this._displayAlert('success', `Registro de ${action} exitoso`);
//
//                 if (result.action === 'check_in') {
//                     this._displayAlert(
//                         'warning',
//                         'Disfrute su tiempo de trabajo. Recuerde que debe registrar su salida al finalizar su jornada laboral.'
//                     );
//                 }
//                 if (result.action === 'check_in') {
//                     localStorage.setItem('attendance_entry_notice', '1');
//                 }
//                 setTimeout(() => window.location.reload(), 3500);
//             }
//         } catch (error) {
//             this._displayAlert('danger', 'Error de conexión con el servidor');
//             btn.disabled = false;
//         }
//     },
//
//     /**
//      * Maneja el evento de guardar cambios en los registros editables
//      */
//     async _onSaveChanges(ev) {
//         const btn = ev.currentTarget;
//         const attendanceId = parseInt(btn.dataset.id);
//         const row = btn.closest('tr');
//
//         const dateInput = row.querySelector('input[data-field="check_in_date"]');
//         const checkInInput = row.querySelector('input[data-field="check_in"]');
//         const checkOutInput = row.querySelector('input[data-field="check_out"]');
//
//         // Validar formato de fecha YYYY-MM-DD
//         const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
//         const dateValue = dateInput.value;
//         if (!dateRegex.test(dateValue)) {
//             this._displayAlert('danger', 'Formato de fecha inválido. Use YYYY-MM-DD');
//             return;
//         }
//
//         // Validar formato HH:MM
//         const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
//
//         const checkIn = checkInInput.value;
//         if (!timeRegex.test(checkIn)) {
//             this._displayAlert('danger', 'Formato de hora de entrada inválido. Use HH:MM');
//             return;
//         }
//
//         let checkOut = null;
//         if (checkOutInput && checkOutInput.value) {
//             checkOut = checkOutInput.value;
//             if (!timeRegex.test(checkOut)) {
//                 this._displayAlert('danger', 'Formato de hora de salida inválido. Use HH:MM');
//                 return;
//             }
//         }
//
//         btn.disabled = true;
//         btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';
//
//         try {
//             const result = await rpc('/my/attendance/update', {
//                 attendance_id: attendanceId,
//                 new_check_in_date: dateValue,
//                 new_check_in: checkIn,
//                 new_check_out: checkOut,
//             });
//
//             if (result.error) {
//                 this._displayAlert('danger', result.error);
//             } else {
//                 this._displayAlert('success', 'Registro actualizado correctamente');
//                 // Actualizar la visualización de la fecha
//                 const dateCell = row.querySelector('td:nth-child(1)');
//                 if (dateCell) {
//                     const dateParts = dateValue.split('-');
//                     dateCell.textContent = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;
//                 }
//                 // Actualizar la duración
//                 const durationCell = row.querySelector('td:nth-child(4)');
//                 if (durationCell) {
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
//     /**
//      * Maneja el registro manual de un día completo
//      */
//     async _onSubmitManualEntry(ev) {
//         ev.preventDefault();
//         const btn = ev.currentTarget;
//         const modal = this.el.querySelector('#manualEntryModal');
//
//         const date = this.el.querySelector('#manualEntryDate').value;
//         const checkIn = this.el.querySelector('#manualCheckIn').value;
//         const checkOut = this.el.querySelector('#manualCheckOut').value;
//
//         // Validaciones
//         if (!date || !checkIn || !checkOut) {
//             this._displayAlert('danger', 'Todos los campos son obligatorios');
//             return;
//         }
//
//         if (checkIn >= checkOut) {
//             this._displayAlert('danger', 'La hora de entrada debe ser anterior a la hora de salida');
//             return;
//         }
//
//         btn.disabled = true;
//         btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';
//
//         try {
//             console.log('Enviando datos:', {date, checkIn, checkOut}); // Para depuración
//
//             const result = await rpc('/my/attendance/manual_entry', {
//                 date: date,
//                 check_in: checkIn,
//                 check_out: checkOut,
//             });
//
//             console.log('Respuesta del servidor:', result); // Para depuración
//
//             if (result.error) {
//                 this._displayAlert('danger', result.error);
//             } else {
//                 this._displayAlert('success', result.message || 'Registro manual guardado correctamente');
//                 // Cerrar el modal y limpiar el formulario
//                 const modalInstance = bootstrap.Modal.getInstance(modal);
//                 modalInstance.hide();
//                 this._resetManualEntryForm();
//                 // Recargar después de 2 segundos
//                 setTimeout(() => window.location.reload(), 2000);
//             }
//         } catch (error) {
//             console.error('Error en la solicitud:', error); // Para depuración
//             this._displayAlert('danger', 'Error al conectar con el servidor: ' + (error.message || ''));
//         } finally {
//             btn.disabled = false;
//             btn.innerHTML = 'Guardar';
//         }
//     },
//
//     /**
//      * Cuando se muestra el modal de registro manual
//      */
//     _onManualModalShown() {
//         // Establecer la fecha por defecto a hoy
//         const today = new Date().toISOString().split('T')[0];
//         const dateInput = this.el.querySelector('#manualEntryDate');
//         dateInput.value = today;
//         dateInput.max = today;
//
//         // Establecer horas por defecto (8:00 - 17:00 con 1h de almuerzo)
//         this.el.querySelector('#manualCheckIn').value = '08:00';
//         this.el.querySelector('#manualCheckOut').value = '17:00';
//     },
//
//     /**
//      * Limpia el formulario de registro manual
//      */
//     _resetManualEntryForm() {
//         const form = this.el.querySelector('#manualEntryForm');
//         if (form) {
//             form.reset();
//         }
//     },
//
//     /**
//      * Muestra una alerta en la interfaz
//      * @param {string} type - Tipo de alerta (success, danger, warning, etc.)
//      * @param {string} message - Mensaje a mostrar
//      */
//     _displayAlert(type, message) {
//         // Limpiar alertas anteriores del mismo tipo
//         const existingAlerts = this.el.querySelectorAll(`.alert.alert-${type}`);
//         existingAlerts.forEach(alert => alert.remove());
//
//         const alert = document.createElement('div');
//         alert.className = `alert alert-${type} mt-2 mb-3`;
//         alert.role = 'alert';
//         alert.innerHTML = `
//             <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
//             ${message}
//         `;
//
//         // Insertar la alerta en un lugar visible
//         const header = this.el.querySelector('.card-header');
//         if (header) {
//             header.insertAdjacentElement('afterend', alert);
//         } else {
//             this.el.insertAdjacentElement('afterbegin', alert);
//         }
//
//         // Configurar autodestrucción después de 5 segundos
//         setTimeout(() => {
//             if (alert.parentNode) {
//                 alert.remove();
//             }
//         }, 5000);
//     },
//
//     /**
//      * Inicialización del widget
//      */
//     start() {
//         // Configurar tooltips para los botones
//         $(this.el).find('[data-bs-toggle="tooltip"]').tooltip({
//             trigger: 'hover',
//             placement: 'top'
//         });
//
//         const notice = localStorage.getItem('attendance_entry_notice');
//         if (notice) {
//             this._displayAlert(
//                 'warning',
//                 'Oye, recuerda que tu jornada laboral es de 8 horas. Si necesitas trabajar más de este tiempo, contacta con tu jefe directo y no olvides registrar tu salida.'
//             );
//             localStorage.removeItem('attendance_entry_notice');
//         }
//
//         return this._super.apply(this, arguments);
//     }
// });
//
// export default publicWidget.registry.AttendancePortalWidget;
