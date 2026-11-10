import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Doctors } from './components/doctors/doctors';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Doctors],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected title = 'Telemedicine';
}