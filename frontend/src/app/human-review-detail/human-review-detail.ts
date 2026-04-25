import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { PipelineService, DetectionResult, ScrapedFrameMinimal, AssetFrameMinimal } from '../core/services/pipeline.service';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { AuthService } from '../core/services/auth.service';
import { SidebarComponent } from '../core/components/sidebar/sidebar';

Chart.register(...registerables);

@Component({
  selector: 'app-human-review-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, BaseChartDirective, SidebarComponent],
  templateUrl: './human-review-detail.html',
  styleUrl: './human-review-detail.css'
})
export class HumanReviewDetail implements OnInit {
  private readonly pipelineService = inject(PipelineService);
  private readonly authService = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  public readonly result = signal<DetectionResult | null>(null);
  public readonly isLoading = signal(true);
  public readonly emailTemplate = signal('');
  public readonly operatorName = signal('JH-XXXX');
  public readonly selectedFramePair = signal<{suspect: ScrapedFrameMinimal, reference: AssetFrameMinimal | null, index: number} | null>(null);

  // Line Chart (Similarity Trend)
  public lineChartData: ChartConfiguration<'line'>['data'] = {
    labels: [],
    datasets: [
      {
        data: [],
        label: 'Similarity Trend',
        backgroundColor: 'rgba(0, 243, 255, 0.1)',
        borderColor: '#00f3ff',
        pointBackgroundColor: '#00f3ff',
        pointBorderColor: '#fff',
        fill: 'origin',
        tension: 0.4
      }
    ]
  };

  public lineChartOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { min: 0, max: 1, grid: { color: '#222' }, ticks: { color: '#666' } },
      x: { grid: { display: false }, ticks: { color: '#666' } }
    },
    plugins: { legend: { display: false } }
  };

  // Scatter Plot (Multi-Hash Distance)
  public scatterChartData: ChartConfiguration<'scatter'>['data'] = {
    datasets: [
      {
        data: [],
        label: 'pHash Similarity',
        backgroundColor: '#00f3ff',
        pointRadius: 6,
      },
      {
        data: [],
        label: 'PDQ Similarity',
        backgroundColor: '#ff3366',
        pointRadius: 6,
        pointStyle: 'rect'
      }
    ]
  };

  public scatterChartOptions: ChartConfiguration<'scatter'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { min: 0, max: 1, title: { display: true, text: 'Similarity', color: '#666' }, grid: { color: '#222' } },
      x: { title: { display: true, text: 'Frame Index', color: '#666' }, grid: { color: '#222' } }
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx) => `Frame ${ctx.parsed.x}: ${((ctx.parsed.y ?? 0) * 100).toFixed(1)}%`
        }
      }
    }
  };

  constructor() {
    const caseId = this.route.snapshot.params['id'];
    if (caseId) {
      this.fetchCase(Number(caseId));
    }
  }

  ngOnInit() {
    this.authService.getMe().subscribe(u => this.operatorName.set(u.operator_id));
  }

  fetchCase(id: number) {
    this.isLoading.set(true);
    this.pipelineService.getReviewCase(id).subscribe({
      next: (data) => {
        this.result.set(data);
        this.prepareCharts(data);
        this.generateEmailTemplate(data);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to fetch case detail', err);
        this.isLoading.set(false);
      }
    });
  }

  prepareCharts(r: DetectionResult) {
    // Line Chart
    this.lineChartData = {
      labels: r.frame_similarities.map((_, i) => `F${i + 1}`),
      datasets: [{ ...this.lineChartData.datasets[0], data: r.frame_similarities }]
    };

    // Scatter Chart
    this.scatterChartData = {
      datasets: [
        {
          ...this.scatterChartData.datasets[0],
          data: r.frame_similarities.map((val, i) => ({ x: i + 1, y: val }))
        },
        {
          ...this.scatterChartData.datasets[1],
          data: r.pdq_similarities.map((val, i) => ({ x: i + 1, y: val }))
        }
      ]
    };
  }

  openFrameModal(index: number) {
    const r = this.result();
    if (!r) return;
    this.selectedFramePair.set({
      suspect: r.suspect_frames[index],
      reference: r.matched_asset_frames[index] || null,
      index: index + 1
    });
  }

  closeModal() {
    this.selectedFramePair.set(null);
  }

  getVerdictClass(verdict: string): string {
    return { 
      VIOLATED: 'badge-violated', 
      FLAG: 'badge-flag', 
      REVIEW: 'badge-review', 
      DROP: 'badge-clean' 
    }[verdict] || '';
  }

  generateEmailTemplate(r: DetectionResult) {
    const date = new Date().toLocaleDateString();
    const template = `
Subject: Copyright Inquiry & Takedown Request – ${r.matched_asset_name || 'Sports Media Content'}

To the Platform Support / Legal Team:

Can you please check the copyright of the content identified below? We have identified this material as a potential unauthorized copy of our proprietary media assets.

If it is confirmed to be our content, can you please take it down immediately?

1. Identification of the Copyrighted Work:
* Official Asset: ${r.matched_asset_name || 'Proprietary Sports Broadcast'}
* Asset Owner: ${r.matched_asset_owner || 'SportGuardian Protected Entity'}
* Proof of Identity: Neural Fingerprint Overlap (${(r.phash_score * 100).toFixed(1)}% match).

2. Identification of the Flagged Material:
* URL: ${r.video_url}
* Platform ID: ${r.platform_video_id}
* Title: ${r.video_title}
* Identified via: ShieldMedia AI Neural Analysis

3. Legal Statement:
I have a good-faith belief that the use of the material in the manner complained of is not authorized by the copyright owner, its agent, or the law. I swear, under penalty of perjury, that the information in this notification is accurate and that I am authorized to act on behalf of the owner of the exclusive rights that are allegedly infringed.

Signed,
SHIELD_MEDIA OPERATOR ${this.operatorName()}
SportGuardian AI Protection Team
Date: ${date}
    `.trim();
    this.emailTemplate.set(template);
  }

  sendEmail() {
    alert('COPYRIGHT TAKEDOWN EMAIL DISPATCHED SUCCESSFULLY.');
    this.router.navigate(['/human-review']);
  }

  getPlatformIcon(platform: string): string {
    return { youtube: '🔴', instagram: '📷', reddit: '🟠' }[platform] || '📹';
  }
}
