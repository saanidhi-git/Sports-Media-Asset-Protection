import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AssetRegisterResponse {
  status: string;
  asset_id: number;
  name: string;
}

export interface AssetFrame {
  id: number;
  frame_number: number;
  file_path: string;
  phash_value?: string;
  pdq_hash?: string;
}

export interface PaginatedFrames {
  frames: AssetFrame[];
  total: number;
  page: number;
  limit: number;
}

export interface Asset {
  id: number;
  asset_name: string;
  owner_company: string;
  match_description: string;
  media_file_path: string;
  scoreboard_file_path: string | null;
  scrap_youtube: boolean;
  scrap_reddit: boolean;
  scrap_instagram: boolean;
  total_frames: number;
  created_at: string;
  status: string;
  user_id: number;
  audio_fp?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class AssetService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = environment.apiUrl;

  registerAsset(data: {
    assetName: string;
    ownerCompany: string;
    matchDescription: string;
    mediaToScrap: any;
    numFrames: number;
    selectedFile: File;
    scoreboardFile: File | null;
  }): Observable<HttpEvent<any>> {
    const formData = new FormData();
    formData.append('asset_name', data.assetName);
    formData.append('owner_company', data.ownerCompany);
    formData.append('match_description', data.matchDescription);
    formData.append('media_to_scrap', JSON.stringify(data.mediaToScrap));
    formData.append('num_frames', data.numFrames.toString());
    formData.append('selected_file', data.selectedFile);
    
    if (data.scoreboardFile) {
      formData.append('scoreboard_file', data.scoreboardFile);
    }

    return this.http.post<any>(`${this.apiUrl}/api/v1/assets/register`, formData, {
      reportProgress: true,
      observe: 'events'
    });
  }

  getAssets(): Observable<Asset[]> {
    return this.http.get<Asset[]>(`${this.apiUrl}/api/v1/assets/`);
  }

  getAsset(id: number): Observable<Asset> {
    return this.http.get<Asset>(`${this.apiUrl}/api/v1/assets/${id}`);
  }

  getAssetFrames(id: number, page: number = 1, limit: number = 10): Observable<PaginatedFrames> {
    return this.http.get<PaginatedFrames>(`${this.apiUrl}/api/v1/assets/${id}/frames?page=${page}&limit=${limit}`);
  }

  deleteAsset(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/api/v1/assets/${id}`);
  }
}
