import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

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

  constructor(private fb: FormBuilder) {}

  loginForm: any;
  signupForm: any;

  ngOnInit(): void {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });

    this.signupForm = this.fb.group({
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
    if (this.loginForm.invalid) return;

    this.loading = true;

    setTimeout(() => {
      this.loading = false;
      console.log('LOGIN:', this.loginForm.value);
    }, 1200);
  }

  onSignup() {
    if (this.signupForm.invalid) return;

    const { password, confirmPassword } = this.signupForm.value;

    if (password !== confirmPassword) {
      this.errorMsg = "Passwords do not match";
      return;
    }

    this.loading = true;

    setTimeout(() => {
      this.loading = false;
      console.log('SIGNUP:', this.signupForm.value);
    }, 1200);
  }

  get lf() {
    return this.loginForm.controls;
  }

  get sf() {
    return this.signupForm.controls;
  }
}
