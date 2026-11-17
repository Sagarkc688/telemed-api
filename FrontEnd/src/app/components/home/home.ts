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
  // icon = a Bootstrap Icons class name
  specialties = [
    { name: 'General Practice', icon: 'bi-clipboard2-pulse', text: 'Everyday health problems' },
    { name: 'Dermatology',      icon: 'bi-bandaid',          text: 'Skin, rashes and acne' },
    { name: 'Cardiology',       icon: 'bi-heart-pulse',      text: 'Heart and blood pressure' },
    { name: 'Paediatrics',      icon: 'bi-emoji-smile',      text: 'Care for children' },
    { name: 'Mental Health',    icon: 'bi-chat-heart',       text: 'Anxiety, mood and sleep' },
    { name: 'Respiratory',      icon: 'bi-lungs',            text: 'Breathing and chest problems' }
  ];

  constructor(protected doctorData: DoctorData) {}
}