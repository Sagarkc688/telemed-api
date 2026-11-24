import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Auth } from '../services/auth';

// only lets logged-in users open the page
export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(Auth);
  const router = inject(Router);

  if (auth.isLoggedIn()) {
    return true;    // OK - open the page
  }

  // not logged in -> login page, then come back here afterwards
  return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};