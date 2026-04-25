import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../core/services/auth.service';

interface ScanJob {
  id: number;
  search_query: string;
  platforms: string[];
  status: string;
  created_at: string;
  completed_at: string | null;
}

interface DetectionResult {
  id: number;
  verdict: string;
  phash_score: number;
  pdq_score: number;
  audio_score: number;
  metadata_score: number;
  final_score: number;
  platform: string;
  video_title: string;
  video_url: string;
  platform_video_id: string;
  frames: string[];
  matched_asset_id: number | null;
  matched_asset_name: string | null;
  uploader: string | null;
  comments: any[];
  like_count: number | null;
  view_count: number | null;
  ai_decision: string | null;
  ai_reason: string | null;
  created_at: string;
}

type Phase = 'form' | 'processing' | 'results';

@Component({
  selector: 'app-scan-job-new',
  standalone: true,
  imports: [CommonModule, RouterModule, ReactiveFormsModule],
  templateUrl: './scan-job-new.html',
  styleUrls: ['./scan-job-new.css', '../home/home.css']
})
export class ScanJobNew implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);

  phase = signal<Phase>('form');
  scanForm!: FormGroup;

  // Processing state
  currentJobId = signal<number | null>(null);
  currentJob = signal<ScanJob | null>(null);
  pollTimer: any = null;
  processingLogs = signal<string[]>([]);

  // Results state
  results = signal<DetectionResult[]>([]);

  operatorName = 'UNKNOWN';
  securityStatus = 'SECURE';

  ngOnInit() {
    const user = this.authService.currentUser();
    if (user) {
      this.operatorName = user.operator_id;
    }

    this.scanForm = this.fb.group({
      search_query: ['', Validators.required],
      youtube_enabled: [true],
      youtube_limit: [3, [Validators.min(0), Validators.max(50)]],
      instagram_enabled: [true],
      instagram_limit: [2, [Validators.min(0), Validators.max(50)]],
      reddit_enabled: [false],
      reddit_limit: [2, [Validators.min(0), Validators.max(50)]],
      num_frames_per_video: [8, [Validators.required, Validators.min(1), Validators.max(100)]]
    });

    // Check for jobId in query params
    this.route.queryParams.subscribe(params => {
      const jobId = params['jobId'];
      if (jobId) {
        this.loadExistingJob(Number(jobId));
      }
    });
  }

  loadExistingJob(jobId: number) {
    this.currentJobId.set(jobId);
    this.phase.set('processing');
    this.http.get<ScanJob>(`/api/pipeline/jobs/${jobId}`).subscribe({
      next: (job) => {
        this.currentJob.set(job);
        if (job.status === 'COMPLETED') {
          this.fetchResults(jobId);
        } else if (job.status === 'FAILED') {
          this.addLog(`JOB FAILED`);
        } else {
          this.startPolling(jobId);
        }
      },
      error: (err) => {
        this.addLog(`ERROR LOADING JOB: ${err.message}`);
      }
    });
  }

  ngOnDestroy() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
    }
  }

  get showOptimizationWarning(): boolean {
    return (this.scanForm.get('num_frames_per_video')?.value || 0) > 40;
  }

  get totalVideos(): number {
    let t = 0;
    if (this.scanForm.get('youtube_enabled')?.value) t += this.scanForm.get('youtube_limit')?.value || 0;
    if (this.scanForm.get('instagram_enabled')?.value) t += this.scanForm.get('instagram_limit')?.value || 0;
    if (this.scanForm.get('reddit_enabled')?.value) t += this.scanForm.get('reddit_limit')?.value || 0;
    return t;
  }

  get anyPlatformEnabled(): boolean {
    return this.scanForm.get('youtube_enabled')?.value
      || this.scanForm.get('instagram_enabled')?.value
      || this.scanForm.get('reddit_enabled')?.value;
  }

  // ── SUBMIT ────────────────────────────────
  onSubmit() {
    if (this.scanForm.invalid || !this.anyPlatformEnabled) return;

    const payload = {
      search_query: this.scanForm.get('search_query')?.value,
      youtube_limit: this.scanForm.get('youtube_enabled')?.value ? (this.scanForm.get('youtube_limit')?.value || 0) : 0,
      instagram_limit: this.scanForm.get('instagram_enabled')?.value ? (this.scanForm.get('instagram_limit')?.value || 0) : 0,
      reddit_limit: this.scanForm.get('reddit_enabled')?.value ? (this.scanForm.get('reddit_limit')?.value || 0) : 0,
      num_frames_per_video: this.scanForm.get('num_frames_per_video')?.value
    };

    this.addLog(`SCAN INITIATED: "${payload.search_query}"`);
    this.addLog(`YT=${payload.youtube_limit}  IG=${payload.instagram_limit}  RD=${payload.reddit_limit}  Frames=${payload.num_frames_per_video}`);

    this.http.post<ScanJob>('/api/pipeline/scan', payload).subscribe({
      next: (job) => {
        this.currentJobId.set(job.id);
        this.currentJob.set(job);
        this.phase.set('processing');
        this.addLog(`JOB CREATED: #${job.id} — status=${job.status}`);
        this.startPolling(job.id);
      },
      error: (err) => {
        console.error(err);
        this.addLog(`ERROR: ${err.error?.detail || err.message}`);
      }
    });
  }

  // ── POLLING ───────────────────────────────
  private startPolling(jobId: number) {
    this.pollTimer = setInterval(() => {
      this.http.get<ScanJob>(`/api/pipeline/jobs/${jobId}`).subscribe({
        next: (job) => {
          this.currentJob.set(job);
          if (job.status === 'COMPLETED') {
            clearInterval(this.pollTimer);
            this.addLog(`JOB COMPLETED at ${job.completed_at}`);
            this.fetchResults(jobId);
          } else if (job.status === 'FAILED') {
            clearInterval(this.pollTimer);
            this.addLog(`JOB FAILED`);
          }
        },
        error: (err) => {
          this.addLog(`POLLING ERROR — retrying...`);
        }
      });
      
      // Also poll live minute-to-minute logs from the backend
      this.http.get<string[]>(`/api/pipeline/jobs/${jobId}/logs`).subscribe({
        next: (serverLogs) => {
          if (serverLogs && serverLogs.length > 0) {
             // We replace the entire local processingLogs array with the server logs
             // But we only do it if there are server logs, to preserve local init logs if the file isn't created yet
             this.processingLogs.set(serverLogs);
             this.scrollToBottom();
          }
        }
      });
      
    }, 3000);
  }

  // ── RESULTS ───────────────────────────────
  private fetchResults(jobId: number) {
    this.http.get<DetectionResult[]>(`/api/pipeline/results/${jobId}`).subscribe({
      next: (data) => {
        this.results.set(data);
        this.addLog(`LOADED ${data.length} detection results`);
        this.phase.set('results');
      },
      error: (err) => {
        console.error(err);
        this.addLog(`RESULTS FETCH ERROR: ${err.message}`);
        this.phase.set('results');
      }
    });
  }

  // ── HELPERS ───────────────────────────────
  private addLog(msg: string) {
    const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
    this.processingLogs.update(logs => [...logs, `[${ts}] [UI] ${msg}`]);
    this.scrollToBottom();
  }
  
  private scrollToBottom() {
    setTimeout(() => {
        const logBox = document.querySelector('.log-box');
        if (logBox) {
            logBox.scrollTop = logBox.scrollHeight;
        }
    }, 100);
  }

  getPlatformIcon(platform: string): string {
    return { youtube: '🔴', instagram: '📷', reddit: '🟠' }[platform] || '📹';
  }

  getVerdictClass(verdict: string): string {
    return { FLAG: 'badge-flag', REVIEW: 'badge-review', DROP: 'badge-clean' }[verdict] || '';
  }

  getVerdictLabel(verdict: string): string {
    return { FLAG: 'VIOLATION', REVIEW: 'REVIEW', DROP: 'CLEAN' }[verdict] || verdict;
  }

  get flagCount(): number {
    return this.results().filter(r => r.verdict === 'FLAG').length;
  }

  get reviewCount(): number {
    return this.results().filter(r => r.verdict === 'REVIEW').length;
  }

  get cleanCount(): number {
    return this.results().filter(r => r.verdict === 'DROP').length;
  }

  goBack() {
    this.phase.set('form');
    this.results.set([]);
    this.processingLogs.set([]);
    this.currentJobId.set(null);
    this.currentJob.set(null);
  }
}
