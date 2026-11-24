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

  // "Why choose us" accordion
  whyItems = [
    { title: 'Real doctors, by video or phone',
      text: 'Every appointment is with a GMC-registered doctor. You choose a video call or a phone call when you book.' },
    { title: 'Book in a couple of minutes',
      text: 'Pick a doctor, choose one of the days they work and a time that suits you. No waiting on hold.' },
    { title: 'Safety first',
      text: 'When you add symptoms before your appointment, we check them. If something could be an emergency, we tell you to call 999 straight away.' },
    { title: 'Your health record in one place',
      text: "See your symptoms, your doctor's notes, follow-up dates and your feedback for every appointment." }
  ];
  openWhy: number | null = 0;    // the first one starts open

  // FAQs accordion
  faqs = [
    { question: 'How do I book an appointment?',
      answer: 'Go to Find a Doctor, choose a doctor who is accepting patients and press Book. You will need to log in as a patient first.' },
    { question: 'What if it is an emergency?',
      answer: 'Do not use this service. Call 999 or go to your nearest Emergency Department straight away.' },
    { question: 'Can I change or cancel my appointment?',
      answer: 'Yes. Open My appointments, show the details of a booked appointment and choose Reschedule or Cancel.' },
    { question: 'Video or phone - which should I choose?',
      answer: 'Video is best when the doctor may need to see something, like a rash. Phone is fine for most other problems.' },
    { question: 'Who can see my information?',
      answer: 'Only you, the doctor you booked with and the site administrator.' }
  ];
  openFaq: number | null = null;  // all start closed

  constructor(protected doctorData: DoctorData) {}

  // click an open item = close it, click a closed one = open it (and close the others)
  toggleWhy(index: number) {
    this.openWhy = this.openWhy == index ? null : index;
  }

  toggleFaq(index: number) {
    this.openFaq = this.openFaq == index ? null : index;
  }
}

