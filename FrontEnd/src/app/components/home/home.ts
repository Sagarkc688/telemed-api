import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { DoctorData } from '../../services/doctor-data';

@Component({
  selector: 'app-home',
  imports: [RouterModule],
  providers: [DoctorData],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home {

  specialties = [
    { name: 'General Practice', icon: '🩺', text: 'Everyday health problems' },
    { name: 'Dermatology',      icon: '🧴', text: 'Skin, rashes and acne' },
    { name: 'Cardiology',       icon: '❤️', text: 'Heart and blood pressure' },
    { name: 'Paediatrics',      icon: '🧸', text: 'Care for children' },
    { name: 'Mental Health',    icon: '🧠', text: 'Anxiety, mood and sleep' },
    { name: 'Respiratory',      icon: '🫁', text: 'Breathing and chest problems' }
  ];

  constructor(protected doctorData: DoctorData) {}

}