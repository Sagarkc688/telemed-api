import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-navigation',
  imports: [RouterModule],
  templateUrl: './navigation.html',
  styleUrl: './navigation.css'
})
export class Navigation {
  menuOpen: boolean = false;

  // ☰ button: open if closed, close if open
  toggleMenu() {
    this.menuOpen = !this.menuOpen;
  }

  // close the phone menu after a link is clicked
  closeMenu() {
    this.menuOpen = false;
  }
}