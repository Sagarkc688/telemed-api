import { Component } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { Auth } from '../../services/auth';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterModule],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class Login {
  loginForm = new FormGroup({
    username: new FormControl('', Validators.required),
    password: new FormControl('', Validators.required)
  });

  errorMessage: string = '';
  loading: boolean = false;
  showPassword: boolean = false;
  sessionExpired: boolean = false;
  returnUrl: string = '/';

  constructor(private auth: Auth,
              private router: Router,
              private route: ActivatedRoute) {}

  ngOnInit() {
    const params = this.route.snapshot.queryParamMap;
    this.sessionExpired = params.get('expired') == 'true';

    // only accept pages INSIDE our app (must start with "/") - safer
    const returnUrl = params.get('returnUrl') || '/';
    // must be inside our app, and never the login page itself (that would loop)
    this.returnUrl = returnUrl.startsWith('/') && !returnUrl.startsWith('/login') ? returnUrl : '/';
  }

  isInvalid(field: string) {
    const control = this.loginForm.get(field);
    return !!control && control.invalid && control.touched;
  }

  onSubmit() {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.errorMessage = '';
    const username = this.loginForm.value.username!;
    const password = this.loginForm.value.password!;

    this.auth.login(username, password).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigateByUrl(this.returnUrl);   // back to where they were
      },
      error: (error) => {
        this.loading = false;
        if (error.status == 401) {
          this.errorMessage = 'Wrong username or password.';
        } else {
          this.errorMessage = "Sorry, we couldn't reach the server. Please try again.";
        }
      }
    });
  }
}