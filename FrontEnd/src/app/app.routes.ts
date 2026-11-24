import { Routes } from '@angular/router';
import { Home } from './components/home/home';
import { Doctors } from './components/doctors/doctors';
import { Doctor } from './components/doctor/doctor';
import { Login } from './components/login/login';

export const routes: Routes = [
  { path: '', component: Home },
  { path: 'doctors', component: Doctors },
  { path: 'doctors/:id', component: Doctor },
  { path: 'login', component: Login }
];