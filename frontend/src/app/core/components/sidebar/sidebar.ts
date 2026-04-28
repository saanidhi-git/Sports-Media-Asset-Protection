import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { LayoutService } from '../../services/layout';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <aside class="sidebar" [class.collapsed]="isCollapsed()">
      <div class="brand">
        <span class="brand-icon">🛡️</span>
        <span class="brand-name" *ngIf="!isCollapsed()">SPORTS GUARDIAN</span>
      </div>

      <button class="toggle-btn" (click)="toggleSidebar()">
        {{ isCollapsed() ? '→' : '←' }}
      </button>
      
      <nav class="nav-links">
        <a routerLink="/home" routerLinkActive="active" class="nav-item" [title]="isCollapsed() ? 'Dashboard' : ''">
          <span class="icon">📊</span>
          <span class="link-text" *ngIf="!isCollapsed()">DASHBOARD</span>
        </a>
        <a routerLink="/register-asset" routerLinkActive="active" class="nav-item" [title]="isCollapsed() ? 'Asset Vault' : ''">
          <span class="icon">📦</span>
          <span class="link-text" *ngIf="!isCollapsed()">ASSET VAULT</span>
        </a>
        <a routerLink="/scan/new" routerLinkActive="active" class="nav-item" [title]="isCollapsed() ? 'New Scan' : ''">
          <span class="icon">📡</span>
          <span class="link-text" *ngIf="!isCollapsed()">NEW SCAN</span>
        </a>
        <a routerLink="/scan/history" routerLinkActive="active" class="nav-item" [title]="isCollapsed() ? 'Scan History' : ''">
          <span class="icon">📜</span>
          <span class="link-text" *ngIf="!isCollapsed()">SCAN HISTORY</span>
        </a>
        <a routerLink="/human-review" routerLinkActive="active" class="nav-item" [title]="isCollapsed() ? 'Human Review' : ''">
          <span class="icon">👥</span>
          <span class="link-text" *ngIf="!isCollapsed()">HUMAN REVIEW</span>
        </a>
      </nav>

      <div class="operator-profile">
        <div class="avatar"></div>
        <div class="info" *ngIf="!isCollapsed()">
          <div class="name">OP: {{ operatorName() }}</div>
          <div class="status">STATUS: <span class="status-optimal">OPTIMAL</span></div>
        </div>
      </div>
    </aside>
  `,
  styles: [`
    .sidebar {
      width: 260px;
      background: #111111;
      border-right: 1px solid #222;
      display: flex;
      flex-direction: column;
      padding: 30px 0;
      position: sticky;
      top: 0;
      height: 100vh;
      transition: width 0.15s ease-out;
      z-index: 100;
    }

    .sidebar.collapsed {
      width: 80px;
    }

    .brand {
      padding: 0 30px;
      margin-bottom: 50px;
      display: flex;
      align-items: center;
      gap: 12px;
      height: 32px;
      overflow: hidden;
    }

    .brand-name {
      font-weight: 800;
      letter-spacing: 2px;
      color: #00f3ff;
      font-size: 16px;
      white-space: nowrap;
    }

    .toggle-btn {
      position: absolute;
      right: -12px;
      top: 35px;
      width: 24px;
      height: 24px;
      background: #00f3ff;
      color: #000;
      border: none;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      box-shadow: 0 0 10px rgba(0, 243, 255, 0.3);
      z-index: 10;
    }

    .nav-links {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .nav-item {
      padding: 16px 30px;
      text-decoration: none;
      color: #a0a0a0;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.5px;
      display: flex;
      align-items: center;
      gap: 16px;
      border-left: 3px solid transparent;
      transition: background 0.15s, color 0.15s;
      overflow: hidden;
    }

    .collapsed .nav-item {
      justify-content: center;
      padding: 20px 0;
      border-left-width: 4px;
    }

    .nav-item .icon {
      font-size: 18px;
      min-width: 20px;
      text-align: center;
    }

    .nav-item:hover {
      background: rgba(255, 255, 255, 0.05);
      color: #fff;
    }

    .nav-item.active {
      background: rgba(0, 243, 255, 0.05);
      color: #00f3ff;
      border-left-color: #00f3ff;
    }

    .operator-profile {
      margin-top: auto;
      padding: 20px 30px;
      border-top: 1px solid #222;
      display: flex;
      align-items: center;
      gap: 12px;
      overflow: hidden;
    }

    .collapsed .operator-profile {
      justify-content: center;
      padding: 20px 0;
    }

    .avatar {
      width: 32px;
      height: 32px;
      background: #252525;
      border: 1px solid #333;
      border-radius: 4px;
      flex-shrink: 0;
    }

    .info .name {
      font-size: 11px;
      font-weight: 700;
      color: #fff;
      white-space: nowrap;
    }

    .info .status {
      font-size: 9px;
      font-weight: 600;
      color: #666;
    }

    .status-optimal {
      color: #00ffaa;
    }

    /* RESPONSIVE OVERRIDES */
    @media (max-width: 992px) {
      .sidebar {
        width: 80px;
      }
      .brand-name, .link-text, .operator-profile .info, .toggle-btn {
        display: none;
      }
      .nav-item {
        justify-content: center;
        padding: 20px 0;
      }
    }
    
    @media (max-width: 768px) {
      .sidebar {
         display: none;
      }
    }
  `]
})
export class SidebarComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly layoutService = inject(LayoutService);
  
  protected readonly operatorName = signal('JH-XXXX');
  protected readonly isCollapsed = this.layoutService.isCollapsed;

  ngOnInit() {
    this.authService.getMe().subscribe({
      next: (user) => this.operatorName.set(user.operator_id),
      error: () => {}
    });
  }

  toggleSidebar() {
    this.layoutService.toggleSidebar();
  }
}
