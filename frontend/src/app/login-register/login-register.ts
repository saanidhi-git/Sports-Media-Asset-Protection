import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/services/auth.service';

@Component({
  selector: 'app-login-register',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login-register.html',
  styleUrl: './login-register.css',
})
export class LoginRegister {
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  
  protected readonly activeTab = signal<'signin' | 'create'>('signin');
  protected email = '';
  protected password = '';
  protected errorMessage = signal<string | null>(null);
  protected successMessage = signal<string | null>(null);

  setTab(tab: 'signin' | 'create') {
    this.activeTab.set(tab);
    this.errorMessage.set(null);
    this.successMessage.set(null);
  }

  submit() {
    if (this.activeTab() === 'signin') {
      this.login();
    } else {
      this.register();
    }
  }

  private login() {
    this.errorMessage.set(null);
    this.authService.login(this.email, this.password).subscribe({
      next: () => {
        this.router.navigate(['/home']);
      },
      error: (err) => {
        console.error('Login failed', err);
        const detail = err.error?.detail;
        this.errorMessage.set(typeof detail === 'string' ? detail : 'Invalid credentials or system offline.');
      }
    });
  }

  private register() {
    this.errorMessage.set(null);
    this.successMessage.set(null);
    this.authService.register(this.email, this.password).subscribe({
      next: (user) => {
        this.successMessage.set(`Account created for ${user.operator_id}. Please sign in.`);
        this.setTab('signin');
        this.password = '';
      },
      error: (err) => {
        console.error('Registration failed', err);
        let msg = 'Registration failed. Try again.';
        
        if (err.status === 0) {
          msg = 'Cannot connect to backend server. Please check your internet or wait for the service to wake up.';
        } else if (err.error?.detail) {
          const detail = err.error.detail;
          if (Array.isArray(detail)) {
            msg = detail[0].msg || JSON.stringify(detail);
          } else {
            msg = detail;
          }
        }
        
        this.errorMessage.set(msg);
      }
    });
  }
}
