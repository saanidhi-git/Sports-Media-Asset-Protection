import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../core/services/auth.service';
import { SidebarComponent } from '../core/components/sidebar/sidebar';

interface ScanJob {
  id: number;
  search_query: string;
  platforms: string[];
  status: string;
  created_at: string;
  completed_at: string | null;
}

@Component({
  selector: 'app-scan-jobs-history',
  standalone: true,
  imports: [CommonModule, RouterModule, SidebarComponent],
  templateUrl: './scan-jobs-history.html',
  styleUrls: ['./scan-jobs-history.css', '../home/home.css']
})
export class ScanJobsHistory implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);

  jobs = signal<ScanJob[]>([]);
  loading = signal<boolean>(true);

  ngOnInit() {
    this.fetchJobs();
  }

  fetchJobs() {
    this.loading.set(true);
    this.http.get<ScanJob[]>('/api/pipeline/jobs').subscribe({
      next: (data) => {
        this.jobs.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error fetching jobs:', err);
        this.loading.set(false);
      }
    });
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'COMPLETED': return 'status-completed';
      case 'FAILED': return 'status-failed';
      case 'PROCESSING': return 'status-processing';
      case 'PENDING': return 'status-pending';
      default: return '';
    }
  }

  getPlatformIcon(platform: string): string {
    return { youtube: '🔴', instagram: '📷', reddit: '🟠' }[platform] || '📹';
  }
}
