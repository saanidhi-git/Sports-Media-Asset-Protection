import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink, Router } from '@angular/router';
import { AssetService, Asset, PaginatedFrames, AssetFrame } from '../core/services/asset.service';
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
  private readonly router = inject(Router);
  private readonly assetService = inject(AssetService);
  private readonly authService = inject(AuthService);

  protected readonly asset = signal<Asset | null>(null);
  protected readonly framesData = signal<PaginatedFrames | null>(null);
  protected readonly operatorName = signal('JH-XXXX');
  protected readonly securityStatus = signal('OPTIMAL');
  protected readonly isLoading = signal(true);
  protected readonly isDeleting = signal(false);
  public readonly currentPage = signal(1);
  public readonly selectedFrame = signal<AssetFrame | null>(null);

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
  
  public openFrameDetails(frame: AssetFrame) {
    this.selectedFrame.set(frame);
  }

  public closeModal() {
    this.selectedFrame.set(null);
  }

  public deleteAsset() {
    const asset = this.asset();
    if (!asset) return;

    if (confirm(`⚠️ WARNING: Are you sure you want to delete asset "${asset.asset_name}"? \n\nThis will permanently remove all associated frames, detection results, and legal reviews from both the database and cloud storage.`)) {
      this.isDeleting.set(true);
      this.assetService.deleteAsset(asset.id).subscribe({
        next: () => {
          alert('Asset and all associated data successfully removed.');
          this.router.navigate(['/home']);
        },
        error: (err) => {
          console.error('Failed to delete asset', err);
          alert('Failed to delete asset. System protocol error.');
          this.isDeleting.set(false);
        }
      });
    }
  }

  getFrameUrl(filePath: string): string {
    if (!filePath) return '';
    
    // Support absolute URLs (Cloudinary/S3)
    if (filePath.startsWith('http://') || filePath.startsWith('https://')) {
      return filePath;
    }

    // Normalize slashes for local paths
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
