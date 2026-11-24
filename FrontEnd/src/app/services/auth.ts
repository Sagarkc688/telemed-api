import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { tap, finalize } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class Auth {
  private apiUrl = 'http://localhost:5001/api/v1.0';

  // the logged-in user (null when logged out)
  // a SIGNAL - anything showing it (like the navbar) updates instantly when it changes
  user = signal<any>(this.readUserFromToken());

  constructor(private http: HttpClient) {}

  // GET /login using Basic Auth -> the API sends back { token }
  login(username: string, password: string) {
    const headers = new HttpHeaders({
      Authorization: 'Basic ' + btoa(username + ':' + password)
    });

    return this.http.get<any>(this.apiUrl + '/login', { headers }).pipe(
      // tap = "do something extra with the answer, without changing it"
      tap(response => {
        sessionStorage.setItem('token', response.token);
        this.user.set(this.readUserFromToken());
      })
    );
  }

  // GET /logout - the API puts the token on its blacklist
  // (the interceptor adds the token header for us)
  logout() {
    return this.http.get(this.apiUrl + '/logout').pipe(
      // finalize = runs at the end whether it worked or failed,
      // so we ALWAYS forget the token on this side
      finalize(() => this.clearToken())
    );
  }
  getToken() {
    return sessionStorage.getItem('token');
  }

  isLoggedIn() {
    return this.user() !== null;
  }

  // forget the token on this side
  clearToken() {
    sessionStorage.removeItem('token');
    this.user.set(null);
  }

  // a JWT has 3 parts: header.PAYLOAD.signature
  // the payload holds the user details - we read it to show the name and role
  private readUserFromToken() {
    const token = sessionStorage.getItem('token');
    if (!token) {
      return null;
    }
    try {
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));

      // expired? (exp is in seconds, Date.now() is in milliseconds)
      if (payload.exp * 1000 < Date.now()) {
        sessionStorage.removeItem('token');
        return null;
      }
      return payload;
    } catch {
      sessionStorage.removeItem('token');   // broken token - throw it away
      return null;
    }
  }
}