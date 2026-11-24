import { Injectable } from '@angular/core';
import jsonData from '../data/doctors.json';

@Injectable({ providedIn: 'root' })
export class DoctorData {
  pageSize: number = 8;

  // all doctors, or only one specialty (used for the home page counts)
  filterDoctors(specialty: string = '') {
    if (specialty) {
      return jsonData.filter(doctor => doctor.specialty == specialty);
    }
    return jsonData;
  }

  getDoctors(page: number, specialty: string = '') {
    let pageStart = (page - 1) * this.pageSize;
    let pageEnd = pageStart + this.pageSize;
    return this.filterDoctors(specialty).slice(pageStart, pageEnd);
  }

  getLastPageNumber(specialty: string = '') {
    return Math.ceil(this.filterDoctors(specialty).length / this.pageSize);
  }

  // Find ONE doctor by their id, e.g. "D101"
  getDoctor(id: string) {
    return jsonData.find(doctor => doctor.doctor_id == id);
  }

  // "Mental Health" -> "spec-mental-health" (colour classes in styles.css)
  specialtyClass(specialty: string) {
    return 'spec-' + specialty.toLowerCase().replace(/ /g, '-');
  }

  // "Mental Health" -> "images/3d/mental-health.png"
  specialtyImage(specialty: string) {
    return 'images/3d/' + specialty.toLowerCase().replace(/ /g, '-') + '.png';
  }

    // ["Tue", "Wed", "Mon"] -> "Mon, Tue, Wed" (week order)
  sortDays(days: string[]) {
    const week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return week.filter(day => days.includes(day)).join(', ');
  }
  
  // each doctor's photo: D101 -> "images/doctors/D101.jpg"
  doctorImage(doctorId: string) {
    return 'images/doctors/' + doctorId + '.jpg';
  }

  // if a photo is missing (e.g. a new doctor added by admin), show a general picture instead
  useFallbackImage(event: Event) {
    (event.target as HTMLImageElement).src = 'images/3d/health-worker.png';
  }

  // a short "About" paragraph built from the doctor's real data
  doctorAbout(doctor: any) {
    const focus: any = {
      'General Practice': 'helps with everyday health problems, check-ups and long-term conditions',
      'Dermatology': 'treats skin, hair and nail problems such as eczema, acne and rashes',
      'Cardiology': 'looks after heart health, including blood pressure, chest pain and palpitations',
      'Paediatrics': 'cares for babies, children and teenagers',
      'Mental Health': 'supports people with anxiety, low mood, stress and sleep problems',
      'Respiratory': 'helps with breathing problems such as asthma, coughs and chest infections'
    };

    // ["Tue", "Mon"] -> "Mondays and Tuesdays" (in week order)
    const week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const fullNames: any = { Mon: 'Mondays', Tue: 'Tuesdays', Wed: 'Wednesdays', Thu: 'Thursdays',
                             Fri: 'Fridays', Sat: 'Saturdays', Sun: 'Sundays' };
    const days = week.filter(day => doctor.available_days.includes(day))
                     .map(day => fullNames[day]);
    const dayText = days.length > 1
      ? days.slice(0, -1).join(', ') + ' and ' + days[days.length - 1]
      : days.join('');

    return doctor.name + ' ' + (focus[doctor.specialty] || 'sees patients online') +
           '. With ' + doctor.years_experience + " years' experience, they are based at " +
           doctor.clinic.name + ' and offer video and phone appointments on ' + dayText + '.';
  }
}