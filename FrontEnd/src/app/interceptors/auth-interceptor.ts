import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { Auth } from '../services/auth';

// runs on EVERY HTTP request the app makes
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(Auth);
  const router = inject(Router);
  const token = auth.getToken();

  // logged in? add the token header - but ONLY for our own API
  if (token && req.url.startsWith('http://localhost:5001')) {
    req = req.clone({ setHeaders: { 'x-access-token': token } });
  }

  return next(req).pipe(
    catchError(error => {
      // 401 on a protected route = token expired or logged out -> log in again
      const isLoginOrLogout = req.url.endsWith('/login') || req.url.endsWith('/logout');
      if (error.status == 401 && token && !isLoginOrLogout) {
        auth.clearToken();
        router.navigate(['/login'], {
          queryParams: { returnUrl: router.url, expired: 'true' }
        });
      }
      return throwError(() => error);   // pass the error on to the component
    })
  );
};