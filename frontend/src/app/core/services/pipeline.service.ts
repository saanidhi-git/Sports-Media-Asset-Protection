import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AssetFrameMinimal {
  frame_number: number;
  file_path: string;
  phash_value?: string;
  pdq_hash?: string;
}

export interface ScrapedFrameMinimal {
  frame_number: number;
  file_path: string;
  phash_value?: string;
  pdq_hash?: string;
}

export interface DetectionResult {
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
  suspect_frames: ScrapedFrameMinimal[];
  matched_asset_id: number | null;
  matched_asset_name: string | null;
  matched_asset_owner: string | null;
  best_ref_frame_path: string | null;
  matched_asset_frames: AssetFrameMinimal[];
  frame_similarities: number[];
  pdq_similarities: number[];
  uploader: string | null;
  comments: any[];
  like_count: number | null;
  view_count: number | null;
  ai_decision: string | null;
  ai_reason: string | null;
  dispatch_status: string;
  dispatched_at: string | null;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class PipelineService {
  private readonly http = inject(HttpClient);

  getStats(): Observable<any> {
    return this.http.get<any>('/api/pipeline/stats');
  }

  getReviewQueue(): Observable<DetectionResult[]> {
    return this.http.get<DetectionResult[]>('/api/pipeline/review-queue');
  }

  getReviewCase(id: number): Observable<DetectionResult> {
    return this.http.get<DetectionResult>(`/api/pipeline/review-queue/${id}`);
  }

  getHealthMatrix(): Observable<any> {
    return this.http.get<any>('/api/health/matrix');
  }

  sendNotice(detectionId: number, recipientEmail: string, subject: string, content: string, attachments?: string[]): Observable<any> {
    return this.http.post<any>('/api/notice/send', {
      detection_id: detectionId,
      recipient_email: recipientEmail,
      subject: subject,
      content: content,
      attachments: attachments || []
    });
  }
}
