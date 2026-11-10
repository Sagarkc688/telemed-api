import { Component } from '@angular/core';
import { DoctorData } from '../../services/doctor-data';

@Component({
  providers: [DoctorData],
  selector: 'app-doctors',
  imports: [],
  templateUrl: './doctors.html',
  styleUrl: './doctors.css'
})
export class Doctors {

  doctor_list : any = [];
  page: number = 1;

  constructor(protected doctorData: DoctorData) {}

  ngOnInit() {
    // go back to the page the user was on before a refresh
    if (sessionStorage['page']) {
      this.page = Number(sessionStorage['page']);
    }
    this.doctor_list = this.doctorData.getDoctors(this.page);
  }

  previousPage() {
    if (this.page > 1) {
      this.page = this.page - 1;
      sessionStorage['page'] = this.page;
      this.doctor_list = this.doctorData.getDoctors(this.page);
    }
  }

  nextPage() {
    if (this.page < this.doctorData.getLastPageNumber()) {
      this.page = this.page + 1;
      sessionStorage['page'] = this.page;
      this.doctor_list = this.doctorData.getDoctors(this.page);
    }
  }

  // "Mental Health" -> "spec-mental-health" (matches the classes in doctors.css)
  specialtyClass(specialty: string) {
    return 'spec-' + specialty.toLowerCase().replace(/ /g, '-');
  }

}