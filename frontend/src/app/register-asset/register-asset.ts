import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'app-register-asset',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './register-asset.html',
  styleUrl: './register-asset.css'
})
export class RegisterAsset {
  protected readonly operatorName = signal('JH-7492');
  protected readonly securityStatus = signal('OPTIMAL');

  protected assetName = '';
  protected ownerCompany = '';
  protected matchDescription = '';
  
  protected mediaToScrap = {
    youtube: false,
    reddit: false,
    instagram: false
  };
  
  protected readonly selectedFile = signal<File | null>(null);
  protected readonly scoreboardFile = signal<File | null>(null);
  protected readonly generatedFrames = signal<string[]>([]);
  protected readonly isProcessing = signal(false);

  constructor(private router: Router) {}

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.selectedFile.set(file);
      this.generateFrames();
    }
  }

  onScoreboardFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.scoreboardFile.set(file);
    }
  }

  generateFrames() {
    this.isProcessing.set(true);
    // Simulate frame generation
    setTimeout(() => {
      const mockFrames = [
        'https://placehold.co/150x100/141414/00f3ff?text=FRAME+1',
        'https://placehold.co/150x100/141414/00f3ff?text=FRAME+2',
        'https://placehold.co/150x100/141414/00f3ff?text=FRAME+3',
        'https://placehold.co/150x100/141414/00f3ff?text=FRAME+4',
      ];
      this.generatedFrames.set(mockFrames);
      this.isProcessing.set(false);
    }, 1500);
  }

  toggleScrapMedia(type: 'youtube' | 'reddit' | 'instagram') {
    this.mediaToScrap[type] = !this.mediaToScrap[type];
  }

  register() {
    console.log('Registering Asset:', {
      name: this.assetName,
      owner: this.ownerCompany,
      description: this.matchDescription,
      file: this.selectedFile()?.name,
      mediaToScrap: this.mediaToScrap
    });
    // Implementation for backend registration
    this.router.navigate(['/home']);
  }

  cancel() {
    this.router.navigate(['/home']);
  }
}
