import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { PipelineService, DetectionResult, ScrapedFrameMinimal, AssetFrameMinimal } from '../core/services/pipeline.service';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { AuthService } from '../core/services/auth.service';
import { SidebarComponent } from '../core/components/sidebar/sidebar';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

Chart.register(...registerables);

@Component({
  selector: 'app-human-review-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, BaseChartDirective, SidebarComponent, FormsModule],
  templateUrl: './human-review-detail.html',
  styleUrl: './human-review-detail.css'
})
export class HumanReviewDetail implements OnInit {
  private readonly pipelineService = inject(PipelineService);
  private readonly authService = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly sanitizer = inject(DomSanitizer);

  public readonly result = signal<DetectionResult | null>(null);
  public readonly isLoading = signal(true);
  public readonly emailTemplate = signal('');
  public readonly emailHtmlTemplate = signal<SafeHtml>('');
  public readonly rawHtmlForDispatch = signal('');
  public readonly operatorName = signal('JH-XXXX');
  public readonly selectedFramePair = signal<{suspect: ScrapedFrameMinimal, reference: AssetFrameMinimal | null, index: number} | null>(null);

  // Dispatch Modal State
  public readonly showDispatchModal = signal(false);
  public readonly recipientEmail = signal('');
  public readonly isDispatching = signal(false);

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
        backgroundColor: '#60a5fa',
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
    
    // Rich HTML Template - Blue and Black Professional Look
    const htmlTemplate = `
      <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; background-color: #000; padding: 2px; border: 1px solid #222; border-radius: 8px; color: #fff;">
        <!-- HEADER: Blue Branding -->
        <div style="background-color: #000; color: #00f3ff; padding: 30px; text-align: center; border-radius: 6px 6px 0 0; border-bottom: 2px solid #00f3ff;">
          <h1 style="margin: 0; font-size: 32px; letter-spacing: 4px; font-weight: 900;">🛡️ SHIELD MEDIA</h1>
          <h2 style="margin: 8px 0 0; font-size: 12px; font-weight: bold; text-transform: uppercase; color: #60a5fa; letter-spacing: 2px;">Enforcement Terminal Notice</h2>
        </div>
        
        <div style="background-color: #0a0a0b; padding: 30px; border-radius: 0 0 6px 6px;">
          <p style="font-size: 13px; color: #00f3ff; text-transform: uppercase; letter-spacing: 1px;"><strong>TO: PLATFORM COMPLIANCE / LEGAL TEAM</strong></p>
          <p style="font-size: 14px; color: #ccc; line-height: 1.6;">
            We are formally notifying you of unauthorized proprietary content hosted on your platform, confirmed through <strong>Neural Fingerprint Synchronization</strong>.
          </p>

          <!-- FORENSIC ANALYSIS SECTION: Blue Highlights -->
          <div style="background-color: rgba(0, 243, 255, 0.02); border: 1px solid rgba(0, 243, 255, 0.1); padding: 20px; border-radius: 4px; margin: 25px 0;">
            <h3 style="color: #00f3ff; margin-top: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">📊 FORENSIC VALIDATION DATA</h3>
            <table style="width: 100%; border-collapse: collapse; color: #fff; font-size: 13px;">
              <tr>
                <td style="padding: 8px 0; color: #888;">pHash Similarity:</td>
                <td style="padding: 8px 0; text-align: right; color: #00f3ff; font-weight: bold;">${(r.phash_score * 100).toFixed(2)}%</td>
              </tr>
              <tr>
                <td style="padding: 8px 0; color: #888;">PDQ Alignment:</td>
                <td style="padding: 8px 0; text-align: right; color: #00f3ff; font-weight: bold;">${(r.pdq_score * 100).toFixed(2)}%</td>
              </tr>
              <tr>
                <td style="padding: 8px 0; color: #888;">Audio Sync Match:</td>
                <td style="padding: 8px 0; text-align: right; color: #00f3ff; font-weight: bold;">${(r.audio_score * 100).toFixed(2)}%</td>
              </tr>
              <tr style="border-top: 1px solid #333;">
                <td style="padding: 12px 0; color: #fff; font-weight: bold;">MATCH CONFIDENCE:</td>
                <td style="padding: 12px 0; text-align: right; color: #00f3ff; font-weight: bold; font-size: 20px;">${(r.final_score * 100).toFixed(2)}%</td>
              </tr>
            </table>
          </div>

          <h3 style="color: #60a5fa; border-bottom: 1px solid #222; padding-bottom: 8px; margin-top: 25px; font-size: 13px; text-transform: uppercase;">📌 MASTER REFERENCE</h3>
          <ul style="font-size: 13px; color: #aaa; line-height: 1.8; list-style-type: none; padding: 0;">
            <li><strong>ASSET:</strong> <span style="color:#eee;">${r.matched_asset_name || 'Proprietary Sports Broadcast'}</span></li>
            <li><strong>OWNER:</strong> <span style="color:#eee;">${r.matched_asset_owner || 'SportGuardian Protected Entity'}</span></li>
          </ul>

          <h3 style="color: #60a5fa; border-bottom: 1px solid #222; padding-bottom: 8px; margin-top: 25px; font-size: 13px; text-transform: uppercase;">🚨 TARGET MATERIAL</h3>
          <ul style="font-size: 13px; color: #aaa; line-height: 1.8; list-style-type: none; padding: 0;">
            <li><strong>SOURCE:</strong> <a href="${r.video_url}" style="color: #00f3ff; text-decoration: none;">${r.video_url}</a></li>
            <li><strong>ID:</strong> ${r.platform_video_id}</li>
            <li><strong>TITLE:</strong> ${r.video_title}</li>
          </ul>

          <div style="background-color: rgba(0, 243, 255, 0.05); border-left: 4px solid #00f3ff; padding: 15px; margin-top: 25px;">
            <p style="margin: 0; font-size: 13px; color: #eee; line-height: 1.6;">
              <strong>ENFORCEMENT ACTION:</strong> Request immediate removal of this material. Forensic visual evidence is attached to this formal inquiry.
            </p>
          </div>

          <div style="margin-top: 30px; font-size: 11px; color: #555; border-top: 1px solid #1a1a1a; padding-top: 15px;">
            <p><strong>LEGAL ATTESTATION:</strong> I have a good-faith belief that use of the material in the manner complained of is not authorized. I swear, under penalty of perjury, that the information in this notification is accurate.</p>
            
            <p style="margin-top: 20px; color: #888;">
              Sincerely,<br>
              <strong style="color: #00f3ff;">SHIELD_MEDIA ENFORCEMENT OPERATOR ${this.operatorName()}</strong><br>
              SportGuardian AI Protection Team<br>
              Date: ${date}
            </p>
          </div>
        </div>
      </div>
    `.trim();

    this.rawHtmlForDispatch.set(htmlTemplate);
    this.emailHtmlTemplate.set(this.sanitizer.bypassSecurityTrustHtml(htmlTemplate));
  }

  openDispatchModal() {
    this.showDispatchModal.set(true);
  }

  closeDispatchModal() {
    this.showDispatchModal.set(false);
  }

  confirmDispatch() {
    if (!this.recipientEmail() || !this.rawHtmlForDispatch()) {
      alert('Recipient email and template are required.');
      return;
    }

    const r = this.result();
    if (!r) return;

    this.isDispatching.set(true);
    const subject = `URGENT: Copyright Takedown Request – ${r.matched_asset_name || 'Sports Media Content'}`;
    
    // Gather attachments: take top 3 frame pairs as evidence
    const attachments: string[] = [];
    const sortedIndices = r.frame_similarities
      .map((score, index) => ({ score, index }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(item => item.index);

    sortedIndices.forEach(idx => {
      if (r.suspect_frames[idx]) attachments.push(r.suspect_frames[idx].file_path);
      if (r.matched_asset_frames[idx]) attachments.push(r.matched_asset_frames[idx].file_path);
    });

    this.pipelineService.sendNotice(
      r.id,
      this.recipientEmail(),
      subject,
      this.rawHtmlForDispatch(),
      attachments
    ).subscribe({
      next: () => {
        this.isDispatching.set(false);
        this.showDispatchModal.set(false);
        alert(`TAKEDOWN NOTICE DISPATCHED WITH ${attachments.length} ATTACHMENTS TO: ${this.recipientEmail()}`);
        this.router.navigate(['/human-review']);
      },
      error: (err) => {
        console.error('Failed to dispatch notice', err);
        this.isDispatching.set(false);
        alert(`Failed to dispatch notice: ${err.error?.detail || err.message}`);
      }
    });
  }

  getPlatformIcon(platform: string): string {
    return { youtube: '🔴', instagram: '📷', reddit: '🟠' }[platform] || '📹';
  }

  getFrameUrl(filePath: string | undefined): string {
    if (!filePath) return '';
    if (filePath.startsWith('http://') || filePath.startsWith('https://')) {
      return filePath;
    }
    const normalizedPath = filePath.replace(/\\/g, '/');
    if (normalizedPath.startsWith('/uploads/')) return normalizedPath;
    if (normalizedPath.includes('uploads/')) {
      return '/' + normalizedPath.substring(normalizedPath.indexOf('uploads/'));
    }
    return '/uploads/' + normalizedPath;
  }
}
