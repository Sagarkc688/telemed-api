import { Routes } from '@angular/router';
import { Home } from './components/home/home';
import { Doctors } from './components/doctors/doctors';

export const routes: Routes = [
  {
    path: '',
    component: Home
  },
  {
    path: 'doctors',
    component: Doctors
  }
];