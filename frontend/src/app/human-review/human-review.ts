import { Component, OnInit, signal, inject } from '@angular/core';
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
  public readonly emailTemplate = signal('');

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

  openReview(result: DetectionResult) {
    this.selectedResult.set(result);
    this.generateEmailTemplate(result);
  }

  closeReview() {
    this.selectedResult.set(null);
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
Subject: DMCA Notice of Copyright Infringement – ${r.matched_asset_name || 'Sports Media Content'}

To the Designated Copyright Agent:

This letter serves as formal notification pursuant to the Digital Millennium Copyright Act (DMCA), 17 U.S.C. § 512(c), regarding the unauthorized use of copyrighted material on your service.

1. Identification of Copyrighted Work:
I am an authorized representative of the owner of the exclusive rights to the following copyrighted material:
* Official Asset: ${r.matched_asset_name || 'Proprietary Sports Broadcast'}
* Matching Profile: Perceptual Hash (${(r.phash_score * 100).toFixed(1)}% match), PDQ Hash (${(r.pdq_score * 100).toFixed(1)}% match).

2. Identification of Infringing Material:
The following material is infringing upon my exclusive rights and I request that you remove it or disable access to it immediately:
* URL: ${r.video_url}
* Platform ID: ${r.platform_video_id}
* Title: ${r.video_title}

3. Contact Information:
If you need to contact me regarding this notice, please use the information below:
* Name: SHIELD_MEDIA OPERATOR ${this.operatorName()}
* Company: SportGuardian AI Protection
* Email: legal@shieldmedia.ai

4. Statement of Good Faith:
I have a good faith belief that the use of the material in the manner complained of is not authorized by the copyright owner, its agent, or the law.

5. Statement of Accuracy/Penalty of Perjury:
I swear, under penalty of perjury, that the information in this notification is accurate and that I am authorized to act on behalf of the owner of the exclusive rights that are allegedly infringed.

6. Signature:
/s/ SHIELD_MEDIA_OP_${this.operatorName()}
Date: ${date}
    `.trim();
    this.emailTemplate.set(template);
  }

  sendEmail() {
    // Dummy action as requested
    alert('COPYRIGHT TAKEDOWN EMAIL SENT TO PLATFORM AGENT');
    this.closeReview();
  }

  getPlatformIcon(platform: string): string {
    return { youtube: '🔴', instagram: '📷', reddit: '🟠' }[platform] || '📹';
  }
}
