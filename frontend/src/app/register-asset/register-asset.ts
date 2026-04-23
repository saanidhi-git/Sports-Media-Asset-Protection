import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AssetService } from '../core/services/asset.service';
import { AuthService } from '../core/services/auth.service';

@Component({
  selector: 'app-register-asset',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './register-asset.html',
  styleUrl: './register-asset.css'
})
export class RegisterAsset implements OnInit {
  private readonly router = inject(Router);
  private readonly assetService = inject(AssetService);
  private readonly authService = inject(AuthService);

  protected readonly operatorName = signal('JH-XXXX');
  protected readonly securityStatus = signal('OPTIMAL');

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
  protected readonly errorMessage = signal<string | null>(null);

  ngOnInit() {
    // Fetch real operator name
    this.authService.getMe().subscribe({
      next: (user) => this.operatorName.set(user.operator_id),
      error: (err) => console.error('Failed to fetch profile', err)
    });
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

    this.assetService.registerAsset({
      assetName: this.assetName,
      ownerCompany: this.ownerCompany,
      matchDescription: this.matchDescription,
      mediaToScrap: this.mediaToScrap,
      numFrames: this.numFrames,
      selectedFile: file,
      scoreboardFile: this.scoreboardFile()
    }).subscribe({
      next: (res) => {
        console.log('Asset registered successfully', res);
        this.router.navigate(['/home']);
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
