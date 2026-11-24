import { Routes } from '@angular/router';
import { Home } from './components/home/home';
import { Doctors } from './components/doctors/doctors';
import { Doctor } from './components/doctor/doctor';
import { Login } from './components/login/login';
import { Appointments } from './components/appointments/appointments';
import { authGuard } from './guards/auth-guard';

export const routes: Routes = [
  { path: '', component: Home },
  { path: 'doctors', component: Doctors },
  { path: 'doctors/:id', component: Doctor },
  { path: 'login', component: Login },
  { path: 'appointments', component: Appointments, canActivate: [authGuard] },
  { path: '**', redirectTo: '' }   // any unknown URL -> home page (must stay LAST)
];