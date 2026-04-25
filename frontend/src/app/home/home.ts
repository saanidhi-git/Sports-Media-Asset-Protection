import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../core/services/auth.service';
import { AssetService, Asset } from '../core/services/asset.service';
import { PipelineService } from '../core/services/pipeline.service';
import { SidebarComponent } from '../core/components/sidebar/sidebar';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink, SidebarComponent],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly assetService = inject(AssetService);
  private readonly pipelineService = inject(PipelineService);
  
  protected readonly userAssets = signal<Asset[]>([]);
  protected readonly totalAssetsCount = signal(0);
  protected readonly violationsFound = signal(0);
  protected readonly pendingReviews = signal(0);

  ngOnInit() {
    this.fetchUserAssets();
    this.fetchStats();
  }

  fetchUserAssets() {
    this.assetService.getAssets().subscribe({
      next: (assets) => {
        this.userAssets.set(assets);
        this.totalAssetsCount.set(assets.length);
      },
      error: (err) => {
        console.error('Failed to fetch assets', err);
      }
    });
  }

  fetchStats() {
    this.pipelineService.getStats().subscribe({
      next: (stats) => {
        this.violationsFound.set(stats.violations_found);
        this.pendingReviews.set(stats.pending_reviews);
      },
      error: (err) => {
        console.error('Failed to fetch stats', err);
      }
    });
  }

  logout() {
    this.authService.logout();
  }
  
  protected readonly systemLogs = [
    { time: '14:20:05', event: 'ENCRYPTION_KEY_ROTATED', node: 'SEC-A1' },
    { time: '14:18:22', event: 'UNAUTHORIZED_ACCESS_BLOCKED', node: 'GATEWAY-04' },    
    { time: '14:15:10', event: 'NEW_ASSET_INGESTED', node: 'STORAGE-B' },
  ];

  getAssetType(asset: Asset): string {
    if (asset.scrap_youtube) return 'YOUTUBE';
    if (asset.scrap_reddit) return 'REDDIT';
    if (asset.scrap_instagram) return 'INSTAGRAM';
    return 'MEDIA';
  }

  getAssetImage(asset: Asset): string {
    const text = encodeURIComponent(asset.asset_name.substring(0, 10));
    return `https://placehold.co/400x400/141414/00f3ff?text=${text}`;
  }
}
