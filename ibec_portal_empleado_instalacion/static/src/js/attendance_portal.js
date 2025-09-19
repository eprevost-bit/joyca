/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";

publicWidget.registry.AttendancePortalWidget = publicWidget.Widget.extend({
    selector: '#attendance_portal_widget, #attendance_portal_widget_home',
    events: {
        // --- Funcionalidad existente ---
        'click .btn-clock-in': '_onClickClock',
        'click .btn-clock-out': '_onClickClock',
        'click .btn-save': '_onSaveChanges',
        'click .btn-delete': '_onDeleteAttendance',
        'click .page-link': '_onPageClick',

        // --- NUEVOS EVENTOS PARA EL MODAL DE REGISTRO MÚLTIPLE ---
        'shown.bs.modal #manualEntryModal': '_onManualIntervalModalShown',
        'click #add-interval-btn': '_onAddInterval',
        'click .btn-remove-interval': '_onRemoveInterval',
        'click #btn-save-manual-intervals': '_onSaveManualIntervals',
    },

    // =================================================================
    // FUNCIONES EXISTENTES (SIN CAMBIOS)
    // =================================================================

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
        // Esta función se mantiene para la tabla de edición rápida
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

        // Aquí iría tu lógica de validación de formatos...

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
                row.remove();
            }
        } catch (error) {
            this._displayAlert('danger', 'Error al conectar con el servidor');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-trash"></i> Eliminar';
        }
    },

    // =================================================================
    // NUEVAS FUNCIONES PARA EL MODAL DE REGISTRO DE INTERVALOS
    // =================================================================

    /**
     * Se ejecuta cuando el modal de registro manual se muestra.
     * Prepara el formulario para un nuevo registro.
     */
    _onManualIntervalModalShown: function () {
        const container = this.el.querySelector('#time-intervals-container');
        // Limpia el contenedor y deja solo una fila limpia como plantilla
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

        // Pone la fecha de hoy por defecto y limita la fecha máxima a hoy
        const dateInput = this.el.querySelector('#manualEntryDate');
        if (dateInput) {
            const today = new Date().toISOString().split('T')[0];
            dateInput.value = today;
            dateInput.max = today;
        }
    },

    /**
     * Clona la primera fila de intervalo y la añade al final.
     */
    _onAddInterval: function () {
        const container = this.el.querySelector('#time-intervals-container');
        const firstRow = container.querySelector('.time-interval-row');
        const newRow = firstRow.cloneNode(true);

        // Limpia los valores de los nuevos inputs y hace visible el botón de eliminar
        newRow.querySelector('.manual-check-in').value = '';
        newRow.querySelector('.manual-check-out').value = '';
        newRow.querySelector('.btn-remove-interval').style.display = 'inline-block';
        
        container.appendChild(newRow);
    },

    /**
     * Elimina la fila de intervalo de tiempo correspondiente al botón clickeado.
     */
    _onRemoveInterval: function (ev) {
        ev.currentTarget.closest('.time-interval-row').remove();
    },

    /**
     * Recopila todos los intervalos, los valida y los envía al backend.
     */
    async _onSaveManualIntervals(ev) {
        const btn = ev.currentTarget;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';

        const date = this.el.querySelector('#manualEntryDate').value;
        if (!date) {
            this._displayAlert('danger', 'Por favor, selecciona una fecha.');
            btn.disabled = false;
            btn.innerHTML = 'Guardar Horarios';
            return;
        }

        const intervals = [];
        const rows = this.el.querySelectorAll('.time-interval-row');
        let isValid = true;

        rows.forEach(row => {
            const checkIn = row.querySelector('.manual-check-in').value;
            const checkOut = row.querySelector('.manual-check-out').value;

            if (checkIn && checkOut) { // Solo procesa si ambos campos tienen valor
                if (checkIn >= checkOut) {
                    this._displayAlert('danger', `La hora de entrada (${checkIn}) debe ser menor que la de salida (${checkOut}).`);
                    isValid = false;
                }
                intervals.push({ check_in: checkIn, check_out: checkOut });
            }
        });

        if (!isValid) {
            btn.disabled = false;
            btn.innerHTML = 'Guardar Horarios';
            return;
        }
        
        if (intervals.length === 0) {
            this._displayAlert('warning', 'No has introducido ningún horario válido para guardar.');
            btn.disabled = false;
            btn.innerHTML = 'Guardar Horarios';
            return;
        }

        try {
            const result = await rpc('/my/attendance/manual_entry_intervals', {
                date: date,
                intervals: intervals,
            });

            if (result.error) {
                this._displayAlert('danger', result.error);
            } else {
                this._displayAlert('success', result.message || 'Horarios guardados correctamente.');
                const modalInstance = bootstrap.Modal.getInstance(this.el.querySelector('#manualEntryModal'));
                modalInstance.hide();
                setTimeout(() => window.location.reload(), 1500);
            }
        } catch (error) {
            this._displayAlert('danger', 'Error de conexión con el servidor.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = 'Guardar Horarios';
        }
    },

    // =================================================================
    // FUNCIONES AUXILIARES (SIN CAMBIOS)
    // =================================================================

    /**
     * Muestra una alerta en la interfaz.
     */
    _displayAlert(type, message) {
        const existingAlerts = this.el.querySelectorAll(`.alert.alert-${type}`);
        existingAlerts.forEach(alert => alert.remove());

        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show mt-2 mb-3`;
        alert.role = 'alert';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        const header = this.el.querySelector('.card-header');
        if (header) {
            header.insertAdjacentElement('afterend', alert);
        } else {
            this.el.insertAdjacentElement('afterbegin', alert);
        }

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
        this._super.apply(this, arguments);
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
    }
});

export default publicWidget.registry.AttendancePortalWidget;
// /** @odoo-module **/

// import publicWidget from "@web/legacy/js/public/public_widget";
// import {rpc} from "@web/core/network/rpc";

// publicWidget.registry.AttendancePortalWidget = publicWidget.Widget.extend({
//     selector: '#attendance_portal_widget, #attendance_portal_widget_home',
//     events: {
//         'click .btn-clock-in': '_onClickClock',
//         'click .btn-clock-out': '_onClickClock',
//         'click .btn-save': '_onSaveChanges',
//         'click .btn-delete': '_onDeleteAttendance',
//         'click .btn-submit-manual': '_onSubmitManualEntry',
//         'shown.bs.modal #manualEntryModal': '_onManualModalShown',
//         'click .page-link': '_onPageClick'
//     },

//     /**
//      * Maneja el click en los enlaces de paginación
//      */
//     _onPageClick(ev) {
//         ev.preventDefault();
//         const url = ev.currentTarget.getAttribute('href');
//         window.location.href = url;
//     },

//     /**
//      * Maneja el evento de clic en los botones de entrada/salida
//      */
//     async _onClickClock(ev) {
//         ev.preventDefault();
//         const btn = ev.currentTarget;
//         btn.disabled = true;

//         try {
//             const result = await rpc('/my/attendance/clock', {});

//             if (result.error) {
//                 this._displayAlert('danger', result.error);
//             } else {
//                 const action = result.action === 'check_in' ? 'ENTRADA' : 'SALIDA';

//                 this._displayAlert('success', `Registro de ${action} exitoso`);

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

//     /**
//      * Maneja el evento de guardar cambios en los registros editables
//      */
//     async _onSaveChanges(ev) {
//         const btn = ev.currentTarget;
//         const attendanceId = parseInt(btn.dataset.id);
//         const row = btn.closest('tr');

//         if (!row) {
//             return;
//         }

//         const dateInput = row.querySelector('input[data-field="check_in_date"]');
//         const checkInInput = row.querySelector('input[data-field="check_in"]');
//         const checkOutInput = row.querySelector('input[data-field="check_out"]');

//         // Validation logic (unchanged)
//         const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
//         const dateValue = dateInput.value;
//         if (!dateRegex.test(dateValue)) {
//             this._displayAlert('danger', 'Formato de fecha inválido. Use YYYY-MM-DD');
//             return;
//         }
//         const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
//         const checkIn = checkInInput.value;
//         if (!timeRegex.test(checkIn)) {
//             this._displayAlert('danger', 'Formato de hora de entrada inválido. Use HH:MM');
//             return;
//         }
//         let checkOut = null;
//         if (checkOutInput && checkOutInput.value) {
//             checkOut = checkOutInput.value;
//             if (!timeRegex.test(checkOut)) {
//                 this._displayAlert('danger', 'Formato de hora de salida inválido. Use HH:MM');
//                 return;
//             }
//         }

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

//                 // More reliable way to find the duration cell
//                 const durationCell = row.querySelector('td:nth-of-type(4)'); // Changed to nth-of-type
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
//                 // Eliminar la fila de la tabla
//                 row.remove();
//             }
//         } catch (error) {
//             this._displayAlert('danger', 'Error al conectar con el servidor');
//         } finally {
//             btn.disabled = false;
//             btn.innerHTML = '<i class="fa fa-trash"></i> Eliminar';
//         }
//     },

//     /**
//      * Maneja el registro manual de un día completo
//      */
//     async _onSubmitManualEntry(ev) {
//         ev.preventDefault();
//         const btn = ev.currentTarget;
//         const modal = this.el.querySelector('#manualEntryModal');

//         const date = this.el.querySelector('#manualEntryDate').value;
//         const checkIn = this.el.querySelector('#manualCheckIn').value;
//         const checkOut = this.el.querySelector('#manualCheckOut').value;

//         // Validaciones
//         if (!date || !checkIn || !checkOut) {
//             this._displayAlert('danger', 'Todos los campos son obligatorios');
//             return;
//         }

//         if (checkIn >= checkOut) {
//             this._displayAlert('danger', 'La hora de entrada debe ser anterior a la hora de salida');
//             return;
//         }

//         btn.disabled = true;
//         btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Guardando...';

//         try {
//             const result = await rpc('/my/attendance/manual_entry', {
//                 date: date,
//                 check_in: checkIn,
//                 check_out: checkOut,
//             });

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
//             this._displayAlert('danger', 'Error al conectar con el servidor: ' + (error.message || ''));
//         } finally {
//             btn.disabled = false;
//             btn.innerHTML = 'Guardar';
//         }
//     },

//     /**
//      * Cuando se muestra el modal de registro manual
//      */
//     _onManualModalShown() {
//         // Establecer la fecha por defecto a hoy
//         const today = new Date().toISOString().split('T')[0];
//         const dateInput = this.el.querySelector('#manualEntryDate');
//         dateInput.value = today;
//         dateInput.max = today;

//         // Establecer horas por defecto (8:00 - 17:00)
//         this.el.querySelector('#manualCheckIn').value = '08:00';
//         this.el.querySelector('#manualCheckOut').value = '17:00';
//     },

//     /**
//      * Limpia el formulario de registro manual
//      */
//     _resetManualEntryForm() {
//         const form = this.el.querySelector('#manualEntryForm');
//         if (form) {
//             form.reset();
//         }
//     },

//     /**
//      * Muestra una alerta en la interfaz
//      * @param {string} type - Tipo de alerta (success, danger, warning, etc.)
//      * @param {string} message - Mensaje a mostrar
//      */
//     _displayAlert(type, message) {
//         // Limpiar alertas anteriores del mismo tipo
//         const existingAlerts = this.el.querySelectorAll(`.alert.alert-${type}`);
//         existingAlerts.forEach(alert => alert.remove());

//         const alert = document.createElement('div');
//         alert.className = `alert alert-${type} mt-2 mb-3`;
//         alert.role = 'alert';
//         alert.innerHTML = `
//             <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
//             ${message}
//         `;

//         // Insertar la alerta en un lugar visible
//         const header = this.el.querySelector('.card-header');
//         if (header) {
//             header.insertAdjacentElement('afterend', alert);
//         } else {
//             this.el.insertAdjacentElement('afterbegin', alert);
//         }

//         // Configurar autodestrucción después de 5 segundos
//         setTimeout(() => {
//             if (alert.parentNode) {
//                 alert.remove();
//             }
//         }, 5000);
//     },

//     /**
//      * Inicialización del widget
//      */
//     start() {
//         // Configurar tooltips para los botones
//         $(this.el).find('[data-bs-toggle="tooltip"]').tooltip({
//             trigger: 'hover',
//             placement: 'top'
//         });

//         const notice = localStorage.getItem('attendance_entry_notice');
//         if (notice) {
//             this._displayAlert(
//                 'warning',
//                 'Oye, recuerda que tu jornada laboral es de 8 horas. Si necesitas trabajar más de este tiempo, contacta con tu jefe directo y no olvides registrar tu salida.'
//             );
//             localStorage.removeItem('attendance_entry_notice');
//         }

//         return this._super.apply(this, arguments);
//     }
// });

// export default publicWidget.registry.AttendancePortalWidget;