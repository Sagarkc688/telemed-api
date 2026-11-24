import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TelemedApi } from '../../services/telemed-api';
import { Auth } from '../../services/auth';
import { TIME_SLOTS, futureDate, toIsoDate } from '../../shared/booking-options';

@Component({
  selector: 'app-appointment-actions',
  imports: [ReactiveFormsModule],
  templateUrl: './appointment-actions.html',
  styleUrl: './appointment-actions.css'
})
export class AppointmentActions {
  // IN: the whole appointment
  @Input({ required: true }) appointment: any;
  // OUT: tell the parent it was deleted (so it can remove it from the list)
  @Output() deleted = new EventEmitter<string>();

  mode: '' | 'reschedule' | 'cancel' | 'delete' = '';
  timeSlots = TIME_SLOTS;
  tomorrow = toIsoDate(new Date(Date.now() + 24 * 60 * 60 * 1000));

  rescheduleForm: any;
  saving: boolean = false;
  message: string = '';
  errorMessage: string = '';

  constructor(private formBuilder: FormBuilder,
              private telemedApi: TelemedApi,
              protected auth: Auth) {}

  ngOnInit() {
    // start with the appointment's current values
    const current = this.appointment.appointment;
    this.rescheduleForm = this.formBuilder.group({
      date: [current.date, [Validators.required, futureDate]],    // our custom validator
      time_slot: [current.time_slot, Validators.required],
      type: [current.type, Validators.required]
    });
  }

  // patients and admins can change booked/pending appointments
  canChange() {
    const status = this.appointment.appointment.status;
    return this.auth.user()?.role != 'doctor' && (status == 'booked' || status == 'pending');
  }

  isAdmin() {
    return this.auth.user()?.role == 'admin';
  }

  open(mode: '' | 'reschedule' | 'cancel' | 'delete') {
    this.mode = mode;
    this.message = '';
    this.errorMessage = '';
  }

  isInvalid(control: string) {
    return this.rescheduleForm.controls[control].invalid &&
           this.rescheduleForm.controls[control].touched;
  }

  // PUT { date, time_slot, type }
  saveReschedule() {
    if (this.rescheduleForm.invalid) {
      this.rescheduleForm.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.telemedApi.updateConsultation(this.appointment._id, this.rescheduleForm.value).subscribe({
      next: () => {
        // update the card on screen straight away
        Object.assign(this.appointment.appointment, this.rescheduleForm.value);
        this.finished('Appointment moved.');
      },
      error: (error) => this.failed(error)
    });
  }

  // PUT { status: 'cancelled' }
  confirmCancel() {
    this.saving = true;
    this.telemedApi.updateConsultation(this.appointment._id, { status: 'cancelled' }).subscribe({
      next: () => {
        this.appointment.appointment.status = 'cancelled';
        this.finished('Appointment cancelled.');
      },
      error: (error) => this.failed(error)
    });
  }

  // DELETE (admin only)
  confirmDelete() {
    this.saving = true;
    this.telemedApi.deleteConsultation(this.appointment._id).subscribe({
      next: () => {
        this.saving = false;
        this.deleted.emit(this.appointment._id);
      },
      error: (error) => this.failed(error)
    });
  }

  private finished(message: string) {
    this.saving = false;
    this.mode = '';
    this.message = message;
  }

  private failed(error: any) {
    this.saving = false;
    this.errorMessage = error.error?.error || error.error?.message ||
                        'Sorry, something went wrong. Please try again.';
  }
}