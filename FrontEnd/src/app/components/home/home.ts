import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { DoctorData } from '../../services/doctor-data';
import { Tilt } from '../../directives/tilt';

@Component({
  selector: 'app-home',
  imports: [RouterModule, Tilt],
  providers: [DoctorData],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home {
  specialties = [
    { name: 'General Practice', text: 'Everyday health problems' },
    { name: 'Dermatology',      text: 'Skin, rashes and acne' },
    { name: 'Cardiology',       text: 'Heart and blood pressure' },
    { name: 'Paediatrics',      text: 'Care for children' },
    { name: 'Mental Health',    text: 'Anxiety, mood and sleep' },
    { name: 'Respiratory',      text: 'Breathing and chest problems' }
  ];

  constructor(protected doctorData: DoctorData) {}
}