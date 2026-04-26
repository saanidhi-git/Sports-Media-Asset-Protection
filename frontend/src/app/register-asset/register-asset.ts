import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AssetService } from '../core/services/asset.service';
import { AuthService } from '../core/services/auth.service';
import { SidebarComponent } from '../core/components/sidebar/sidebar';
import { HttpEventType } from '@angular/common/http';

@Component({
  selector: 'app-register-asset',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent],
  templateUrl: './register-asset.html',
  styleUrl: './register-asset.css'
})
export class RegisterAsset implements OnInit {
  private readonly router = inject(Router);
  private readonly assetService = inject(AssetService);
  private readonly authService = inject(AuthService);

  protected assetName = '';
  protected ownerCompany = '';
  protected matchDescription = '';
  protected numFrames = 50;
  
  protected mediaToScrap = {
    youtube: false,
    reddit: false,
    instagram: false
  };
  
  protected readonly selectedFile = signal<File | null>(null);
  protected readonly scoreboardFile = signal<File | null>(null);
  protected readonly generatedFrames = signal<string[]>([]);
  protected readonly isProcessing = signal(false);
  protected readonly isSubmitting = signal(false);
  protected readonly uploadProgress = signal<number>(0);
  protected readonly errorMessage = signal<string | null>(null);

  ngOnInit() {
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.selectedFile.set(file);
    }
  }

  onScoreboardFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.scoreboardFile.set(file);
    }
  }

  toggleScrapMedia(type: 'youtube' | 'reddit' | 'instagram') {
    this.mediaToScrap[type] = !this.mediaToScrap[type];
  }

  register() {
    const file = this.selectedFile();
    if (!file || !this.assetName) return;

    this.isSubmitting.set(true);
    this.errorMessage.set(null);
    this.uploadProgress.set(0);

    this.assetService.registerAsset({
      assetName: this.assetName,
      ownerCompany: this.ownerCompany,
      matchDescription: this.matchDescription,
      mediaToScrap: this.mediaToScrap,
      numFrames: this.numFrames,
      selectedFile: file,
      scoreboardFile: this.scoreboardFile()
    }).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress) {
          const progress = Math.round(100 * event.loaded / (event.total || file.size));
          this.uploadProgress.set(progress);
        } else if (event.type === HttpEventType.Response) {
          console.log('Asset registered successfully', event.body);
          this.router.navigate(['/home']);
        }
      },
      error: (err) => {
        console.error('Asset registration failed', err);
        this.errorMessage.set(err.error?.detail || 'Failed to register asset. System protocol error.');
        this.isSubmitting.set(false);
      }
    });
  }

  cancel() {
    this.router.navigate(['/home']);
  }
}
