import { Component } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { Auth } from '../../services/auth';

@Component({
  selector: 'app-navigation',
  imports: [RouterModule],
  templateUrl: './navigation.html',
  styleUrl: './navigation.css'
})
export class Navigation {
  menuOpen: boolean = false;

  constructor(protected auth: Auth, protected router: Router) {}

  toggleMenu() {
    this.menuOpen = !this.menuOpen;
  }

  closeMenu() {
    this.menuOpen = false;
  }

  // the page to come back to after logging in - never the login page itself
  returnUrl() {
    return this.router.url.startsWith('/login') ? '/' : this.router.url;
  }

  logout() {
    this.closeMenu();
    // go home whether the API call works or not (the token is forgotten either way)
    this.auth.logout().subscribe({
      complete: () => this.router.navigate(['/']),
      error: () => this.router.navigate(['/'])
    });
  }
}