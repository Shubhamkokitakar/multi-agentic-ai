import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../services/auth-service';
import { Router } from '@angular/router';
import { Spinner } from '../shared/spinner/spinner';

@Component({
  standalone: true,
  selector: 'app-login',
  imports: [FormsModule,CommonModule,ReactiveFormsModule,Spinner],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
 mode: 'login' | 'signup' = 'login';

  loading = false;
  errorMsg = '';
  successMsg = '';

  constructor(private fb: FormBuilder, private authService:AuthService,  private router: Router) {}

  loginForm: any;
  signupForm: any;

  ngOnInit(): void {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });

    this.signupForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });
  }

  switchMode(mode: 'login' | 'signup') {
    this.mode = mode;
    this.errorMsg = '';
  }

  onLogin() {
    this.loginForm.markAllAsTouched();

    if (this.loginForm.invalid) return;

    this.loading = true;
    this.errorMsg = '';
    this.successMsg = '';

    const payload = {
      email: this.loginForm.value.email,
      password: this.loginForm.value.password
    };

    this.authService.login(payload).subscribe({
      next: (res) => {
        this.loading = false;
        this.successMsg = 'Login successful! Redirecting to chat...';
        console.log('LOGIN SUCCESS:', res);

        setTimeout(() => {
          this.router.navigate(['/chat']);
        }, 700);

        localStorage.setItem('token', res.access_token);
      },
      error: (err) => {
        this.loading = false;
        this.errorMsg = err?.error?.message || 'Login failed';
        this.successMsg = '';
        console.error(err);
      }
    });
  }

  onSignup() {
    this.signupForm.markAllAsTouched();

    if (this.signupForm.invalid) return;

    const { email, password } = this.signupForm.value;

    this.loading = true;
    this.errorMsg = '';
    this.successMsg = '';

    const payload = {
      email,
      password
    };

    this.authService.signup(payload).subscribe({
      next: (res) => {
        this.loading = false;
        this.successMsg = 'Signup successful! Redirecting to login...';
        console.log('SIGNUP SUCCESS:', res);
        
        setTimeout(() => {
          this.mode = 'login';
          this.signupForm.reset();
          this.successMsg = '';
        }, 1500);
      },
      error: (err) => {
        console.log(err.error.detail,'error');
        this.loading = false;
        this.errorMsg = err?.error?.detail || 'Signup failed';
      }
    });
  }

  get lf() {
    return this.loginForm.controls;
  }

  get sf() {
    return this.signupForm.controls;
  }
}
