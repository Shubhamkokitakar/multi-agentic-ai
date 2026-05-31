import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../services/auth-service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  imports: [FormsModule,CommonModule,ReactiveFormsModule],
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
      username: ['', [Validators.required]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });

    this.signupForm = this.fb.group({
      username: ['', [Validators.required]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]]
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
    username: this.loginForm.value.username,
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

      // optional: store token if backend sends it
      // localStorage.setItem('token', res.token);
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

    const { username, email, password, confirmPassword } = this.signupForm.value;

    if (password !== confirmPassword) {
      this.errorMsg = 'Passwords do not match';
      this.successMsg = '';
      return;
    }

    this.loading = true;
    this.errorMsg = '';
    this.successMsg = '';

    const payload = {
      username,
      email,
      password
    };

    this.authService.signup(payload).subscribe({
      next: (res) => {
        this.loading = false;
        this.successMsg = 'Signup successful! You can now login.';
        console.log('SIGNUP SUCCESS:', res);
      },
      error: (err) => {
        this.loading = false;
        this.errorMsg = err?.error?.message || 'Signup failed';
        console.error(err);
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
