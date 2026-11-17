import { Injectable } from '@angular/core';
import jsonData from '../data/doctors.json';

@Injectable({
  providedIn: 'root',
})
export class DoctorData {

  pageSize: number = 8;

  // all doctors, or only one specialty if a specialty is given
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

  // "Mental Health" -> "spec-mental-health" (colour classes in styles.css)
  specialtyClass(specialty: string) {
    return 'spec-' + specialty.toLowerCase().replace(/ /g, '-');
  }

}