import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ScanRequest {
  search_query: string;
  platforms: string[];
}

export interface ScanJob {
  id: number;
  search_query: string;
  platforms: string[];
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface DetectionResult {
  id: number;
  scraped_video_id: number;
  matched_asset_id: number | null;
  phash_score: number;
  pdq_score: number;
  audio_score: number;
  metadata_score: number;
  final_score: number;
  verdict: string;
  ai_decision: string | null;
  ai_reason: string | null;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class PipelineService {
  private readonly http = inject(HttpClient);

  startScan(data: ScanRequest): Observable<ScanJob> {
    return this.http.post<ScanJob>('/api/pipeline/scan', data);
  }

  getScanJobs(): Observable<ScanJob[]> {
    return this.http.get<ScanJob[]>('/api/pipeline/jobs');
  }

  getResults(jobId?: number): Observable<DetectionResult[]> {
    const url = jobId ? `/api/pipeline/results?job_id=${jobId}` : '/api/pipeline/results';
    return this.http.get<DetectionResult[]>(url);
  }
}
