import { Component } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { DoctorData } from '../../services/doctor-data';
import { TelemedApi } from '../../services/telemed-api';
import { Tilt } from '../../directives/tilt';

@Component({
  selector: 'app-doctors',
  imports: [RouterModule, Tilt],
  providers: [DoctorData, TelemedApi],
  templateUrl: './doctors.html',
  styleUrl: './doctors.css'
})
export class Doctors {
  doctor_list: any = [];
  specialty: string = '';
  loading: boolean = true;
  errorMessage: string = '';

  constructor(protected doctorData: DoctorData,
              private telemedApi: TelemedApi,
              private route: ActivatedRoute) {}

  ngOnInit() {
    // runs again every time ?specialty= changes
    this.route.queryParamMap.subscribe(params => {
      this.specialty = params.get('specialty') || '';
      this.loadDoctors();
    });
  }

  // ask the API (MongoDB) for the doctors
  loadDoctors() {
    this.loading = true;
    this.errorMessage = '';

    this.telemedApi.getDoctors(this.specialty).subscribe({
      next: (response) => {
        this.doctor_list = response;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = "Sorry, we couldn't load the doctors. Please check the API is running.";
        this.loading = false;
      }
    });
  }
}