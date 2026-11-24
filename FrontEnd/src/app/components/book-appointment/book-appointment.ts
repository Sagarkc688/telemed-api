import { Component } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { DatePipe, TitleCasePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { switchMap, catchError, of } from 'rxjs';
import { TelemedApi } from '../../services/telemed-api';
import { DoctorData } from '../../services/doctor-data';
import { Auth } from '../../services/auth';
import { TIME_SLOTS, nextWorkingDates, toIsoDate } from '../../shared/booking-options';

@Component({
  selector: 'app-book-appointment',
  imports: [RouterModule, ReactiveFormsModule, DatePipe, TitleCasePipe],
  providers: [DoctorData],
  templateUrl: './book-appointment.html',
  styleUrl: './book-appointment.css'
})
export class BookAppointment {
  doctor: any = null;
  loading: boolean = true;
  notFound: boolean = false;
  saving: boolean = false;
  booked: boolean = false;
  errorMessage: string = '';

  dates: { iso: string, date: Date }[] = [];
  timeSlots = TIME_SLOTS;
  bookingForm: any;

  constructor(private formBuilder: FormBuilder,
              private telemedApi: TelemedApi,
              protected doctorData: DoctorData,
              protected auth: Auth,
              private route: ActivatedRoute) {}

  ngOnInit() {
    this.bookingForm = this.formBuilder.group({
      type: ['video', Validators.required],
      date: ['', Validators.required],
      time_slot: ['', Validators.required],
      patient_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]]
    });

    // load the doctor from the API (by MongoDB _id in the URL)
    this.route.paramMap.pipe(
      switchMap(params =>
        this.telemedApi.getDoctor(params.get('id') || '').pipe(
          catchError(() => {
            this.notFound = true;
            return of(null);
          })
        )
      )
    ).subscribe(doctor => {
      this.doctor = doctor;
      this.loading = false;
      if (doctor) {
        // only the days this doctor works
        this.dates = nextWorkingDates(doctor.available_days)
                       .map(date => ({ iso: toIsoDate(date), date: date }));
      }
    });
  }

  isInvalid(control: string) {
    return this.bookingForm.controls[control].invalid &&
           this.bookingForm.controls[control].touched;
  }

  onSubmit() {
    if (this.bookingForm.invalid) {
      this.bookingForm.markAllAsTouched();
      return;
    }

    this.saving = true;
    this.errorMessage = '';

    // the form values + the doctor + the email from the login token
    // (the email MUST match the token so the patient can see it in "My appointments")
    const booking = {
      ...this.bookingForm.value,
      doctor_id: this.doctor.doctor_id,
      patient_email: this.auth.user().email
    };

    this.telemedApi.bookConsultation(booking).subscribe({
      next: () => {
        this.saving = false;
        this.booked = true;
      },
      error: (error) => {
        this.saving = false;
        this.errorMessage = error.error?.error || error.error?.message ||
                            "Sorry, we couldn't book that. Please try again.";
      }
    });
  }
}