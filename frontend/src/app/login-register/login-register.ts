import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login-register',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './login-register.html',
  styleUrl: './login-register.css',
})
export class LoginRegister {
  private readonly router = inject(Router);
  protected readonly activeTab = signal<'signin' | 'create'>('signin');

  setTab(tab: 'signin' | 'create') {
    this.activeTab.set(tab);
  }

  login() {
    // Logic for authentication would go here
    this.router.navigate(['/home']);
  }
}
