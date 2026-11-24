import { AbstractControl, ValidationErrors } from '@angular/forms';

// half-hour appointment times: 09:00, 09:30 ... 16:30
export const TIME_SLOTS: string[] = [];
for (let hour = 9; hour < 17; hour++) {
  const hh = String(hour).padStart(2, '0');
  TIME_SLOTS.push(hh + ':00');
  TIME_SLOTS.push(hh + ':30');
}

// Date -> "2026-11-24" (the format the API uses)
// built by hand because toISOString() uses UTC and could give the wrong day
export function toIsoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return year + '-' + month + '-' + day;
}

// the next few dates the doctor works, starting tomorrow
// e.g. available_days ["Mon", "Wed"] -> the next 10 Mondays and Wednesdays
export function nextWorkingDates(availableDays: string[], count: number = 10): Date[] {
  const dates: Date[] = [];
  const today = new Date();

  for (let i = 1; dates.length < count && i <= 60; i++) {
    const date = new Date(today);
    date.setDate(today.getDate() + i);
    const dayName = date.toLocaleDateString('en-GB', { weekday: 'short' });   // "Mon"
    const works = availableDays.some(d => d.substring(0, 3).toLowerCase() == dayName.toLowerCase());
    if (works) {
      dates.push(date);
    }
  }
  return dates;
}

// CUSTOM VALIDATOR: the date must be after today
export function futureDate(control: AbstractControl): ValidationErrors | null {
  if (!control.value) {
    return null;                       // empty is handled by Validators.required
  }
  // "YYYY-MM-DD" strings sort in date order, so > works
  return control.value > toIsoDate(new Date()) ? null : { notFuture: true };
}