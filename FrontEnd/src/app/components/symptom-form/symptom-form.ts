import { Component, EventEmitter, Input, Output } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { TelemedApi } from '../../services/telemed-api';

@Component({
  selector: 'app-symptom-form',
  imports: [ReactiveFormsModule],
  templateUrl: './symptom-form.html',
  styleUrl: './symptom-form.css'
})
export class SymptomForm {
  // IN: which consultation this form belongs to (given by the parent)
  @Input({ required: true }) consultationId: string = '';

  // OUT: tells the parent "a symptom was added" (with the API's answer)
  @Output() symptomAdded = new EventEmitter<any>();

  // IN: the symptoms this appointment already has (to stop duplicates)
  @Input() existingSymptoms: any[] = [];

  // OUR OWN VALIDATOR - an error if this symptom is already on the appointment
  // (an arrow function so "this" still means this component)
  noDuplicate = (control: AbstractControl): ValidationErrors | null => {
    const name = (control.value || '').trim().toLowerCase();
    const alreadyThere = this.existingSymptoms.some(
      (symptom: any) => symptom.name.toLowerCase() == name
    );
    return alreadyThere ? { duplicate: true } : null;
  };

  symptomForm: any;
  saving: boolean = false;
  successMessage: string = '';
  errorMessage: string = '';
  warning: string = '';

  // suggestions shown while typing (the user can still type anything)
  suggestions = ['Headache', 'Fever', 'Cough', 'Sore throat', 'Rash', 'Back pain',
                 'Low mood', 'Anxiety', 'Chest pain', 'Difficulty breathing'];

  constructor(private formBuilder: FormBuilder, private telemedApi: TelemedApi) {}

  ngOnInit() {
    // FE15: FormBuilder - [starting value, validators]
    this.symptomForm = this.formBuilder.group({
      name: ['', [Validators.required, Validators.maxLength(60), this.noDuplicate]],
      severity: [5, [Validators.required, Validators.min(1), Validators.max(10)]],
      duration_days: [1, [Validators.required, Validators.min(1), Validators.max(365)]]
    });
  }

  // FE15: true when a field is wrong AND the user has touched it
  isInvalid(control: string) {
    return this.symptomForm.controls[control].invalid &&
           this.symptomForm.controls[control].touched;
  }

  // 1-3 Mild, 4-7 Moderate, 8-10 Severe
  severityWord() {
    const severity = this.symptomForm.value.severity;
    if (severity >= 8) return 'Severe';
    if (severity >= 4) return 'Moderate';
    return 'Mild';
  }

  onSubmit() {
    if (this.symptomForm.invalid) {
      this.symptomForm.markAllAsTouched();
      return;
    }

    this.saving = true;
    this.successMessage = '';
    this.errorMessage = '';
    this.warning = '';

    this.telemedApi.addSymptom(this.consultationId, this.symptomForm.value).subscribe({
      next: (response) => {
        this.saving = false;
        this.successMessage = 'Symptom added. Urgency is now ' + response.urgency_level + '.';
        if (response.warning) {
          this.warning = response.warning;     // the API's 999 message
        }
        this.symptomAdded.emit(response);      // tell the parent page
        // FE15: reset the form (back to the starting values)
        this.symptomForm.reset({ name: '', severity: 5, duration_days: 1 });
      },
      error: (error) => {
        this.saving = false;
        // show the API's own message if it sent one
        this.errorMessage = error.error?.error || "Sorry, we couldn't add that symptom. Please try again.";
      }
    });
  }
}