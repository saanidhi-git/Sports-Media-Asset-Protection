import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login-register',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './login-register.html',
  styleUrl: './login-register.css',
})
export class LoginRegister {
  protected readonly activeTab = signal<'signin' | 'create'>('signin');

  setTab(tab: 'signin' | 'create') {
    this.activeTab.set(tab);
  }
}
