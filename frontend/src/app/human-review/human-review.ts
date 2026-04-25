import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { PipelineService, DetectionResult } from '../core/services/pipeline.service';
import { AuthService } from '../core/services/auth.service';
import { SidebarComponent } from '../core/components/sidebar/sidebar';

@Component({
  selector: 'app-human-review',
  standalone: true,
  imports: [CommonModule, RouterLink, SidebarComponent],
  templateUrl: './human-review.html',
  styleUrl: './human-review.css'
})
export class HumanReview implements OnInit {
  private readonly pipelineService = inject(PipelineService);
  private readonly authService = inject(AuthService);

  public readonly results = signal<DetectionResult[]>([]);
  public readonly isLoading = signal(true);
  public readonly operatorName = signal('JH-XXXX');
  public readonly selectedResult = signal<DetectionResult | null>(null);
  
  public readonly pendingResults = computed(() => 
    this.results().filter(r => r.dispatch_status === 'PENDING')
  );

  public readonly dispatchedResults = computed(() => 
    this.results().filter(r => r.dispatch_status === 'DISPATCHED')
  );

  ngOnInit() {
    this.fetchQueue();
    this.authService.getMe().subscribe({
      next: (user) => this.operatorName.set(user.operator_id)
    });
  }

  fetchQueue() {
    this.isLoading.set(true);
    this.pipelineService.getReviewQueue().subscribe({
      next: (data) => {
        this.results.set(data);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to fetch review queue', err);
        this.isLoading.set(false);
      }
    });
  }

  getVerdictClass(verdict: string): string {
    return { 
      VIOLATED: 'badge-violated', 
      FLAG: 'badge-flag', 
      REVIEW: 'badge-review', 
      DROP: 'badge-clean' 
    }[verdict] || '';
  }

  getPlatformIcon(platform: string): string {
    return { youtube: '🔴', instagram: '📷', reddit: '🟠' }[platform] || '📹';
  }
}
