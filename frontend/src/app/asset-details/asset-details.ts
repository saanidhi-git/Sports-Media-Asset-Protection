import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AssetService, Asset, PaginatedFrames } from '../core/services/asset.service';
import { AuthService } from '../core/services/auth.service';

@Component({
  selector: 'app-asset-details',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './asset-details.html',
  styleUrl: './asset-details.css'
})
export class AssetDetails implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly assetService = inject(AssetService);
  private readonly authService = inject(AuthService);

  protected readonly asset = signal<Asset | null>(null);
  protected readonly framesData = signal<PaginatedFrames | null>(null);
  protected readonly operatorName = signal('JH-XXXX');
  protected readonly securityStatus = signal('OPTIMAL');
  protected readonly isLoading = signal(true);
  protected readonly currentPage = signal(1);

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (id) {
      this.fetchAssetDetails(id);
      this.fetchFrames(id, 1);
    }

    this.authService.getMe().subscribe({
      next: (user) => this.operatorName.set(user.operator_id)
    });
  }

  fetchAssetDetails(id: number) {
    this.assetService.getAsset(id).subscribe({
      next: (asset) => {
        this.asset.set(asset);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to fetch asset details', err);
        this.isLoading.set(false);
      }
    });
  }

  fetchFrames(id: number, page: number) {
    this.assetService.getAssetFrames(id, page, 10).subscribe({
      next: (data) => {
        this.framesData.set(data);
        this.currentPage.set(page);
      }
    });
  }

  nextPage() {
    const data = this.framesData();
    if (data && this.currentPage() * data.limit < data.total) {
      this.fetchFrames(this.asset()!.id, this.currentPage() + 1);
    }
  }

  prevPage() {
    if (this.currentPage() > 1) {
      this.fetchFrames(this.asset()!.id, this.currentPage() - 1);
    }
  }

  getFrameUrl(filePath: string): string {
    if (!filePath) return '';
    
    // Normalize slashes
    const normalizedPath = filePath.replace(/\\/g, '/');
    
    // If the path already starts with /uploads, return it
    if (normalizedPath.startsWith('/uploads/')) {
      return normalizedPath;
    }
    
    // If it contains uploads/, extract everything from uploads onwards
    if (normalizedPath.includes('uploads/')) {
      return '/' + normalizedPath.substring(normalizedPath.indexOf('uploads/'));
    }
    
    // Fallback: if it's just a filename or relative path, prepend /uploads/
    return '/uploads/' + normalizedPath;
  }
}
