import { Component } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { DoctorData } from '../../services/doctor-data';

@Component({
  providers: [DoctorData],
  selector: 'app-doctors',
  imports: [RouterModule],
  templateUrl: './doctors.html',
  styleUrl: './doctors.css'
})
export class Doctors {

  doctor_list : any = [];
  page: number = 1;
  specialty: string = '';

  constructor(protected doctorData: DoctorData,
              private route: ActivatedRoute) {}

  ngOnInit() {
    // runs every time the ?specialty= part of the URL changes
    this.route.queryParamMap.subscribe(params => {
      this.specialty = params.get('specialty') || '';

      // same filter as before -> remember the page, new filter -> start at page 1
      if (sessionStorage['specialty'] == this.specialty && sessionStorage['page']) {
        this.page = Number(sessionStorage['page']);
      } else {
        this.page = 1;
      }
      sessionStorage['specialty'] = this.specialty;
      sessionStorage['page'] = this.page;

      this.loadDoctors();
    });
  }

  loadDoctors() {
    this.doctor_list = this.doctorData.getDoctors(this.page, this.specialty);
  }

  previousPage() {
    if (this.page > 1) {
      this.page = this.page - 1;
      sessionStorage['page'] = this.page;
      this.loadDoctors();
    }
  }

  nextPage() {
    if (this.page < this.doctorData.getLastPageNumber(this.specialty)) {
      this.page = this.page + 1;
      sessionStorage['page'] = this.page;
      this.loadDoctors();
    }
  }

}