import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
import { Navigation } from './components/navigation/navigation';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, Navigation],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected title = 'Telemedicine';
  protected year = new Date().getFullYear();
}