import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './home.html',
  styleUrl: './home.css'
})
export class Home {
  protected readonly operatorName = signal('JH-7492');
  protected readonly securityStatus = signal('OPTIMAL');
  
  protected readonly securedAssets = [
    { name: 'IPL 2024: CSK vs RCB', type: 'CRICKET', img: 'https://placehold.co/400x400/141414/00f3ff?text=IPL+MATCH' },
    { name: 'UEFA CHAMPIONS LEAGUE', type: 'FOOTBALL', img: 'https://placehold.co/400x400/141414/39FF14?text=FOOTBALL' },
    { name: 'WIMBLEDON FINALS', type: 'TENNIS', img: 'https://placehold.co/400x400/141414/00f3ff?text=TENNIS' },
    { name: 'NBA ALL STAR 2024', type: 'BASKETBALL', img: 'https://placehold.co/400x400/141414/39FF14?text=NBA' },
  ];

  protected readonly assets = [
    { id: 'ASSET-01', name: 'PREMIER_LEAGUE_FINALS_B-ROLL', status: 'PROTECTED', encryption: 'AES-256' },
    { id: 'ASSET-02', name: 'SUPERBOWL_LVII_HIGHLIGHTS_RAW', status: 'MONITORING', encryption: 'RSA-4096' },
    { id: 'ASSET-03', name: 'WIMBLEDON_VR_EXPERIENCE', status: 'PROTECTED', encryption: 'AES-256' },
    { id: 'ASSET-04', name: 'NBA_ALL_STAR_MICD_UP', status: 'ALERT', encryption: 'PENDING' },
  ];

  protected readonly systemLogs = [
    { time: '14:20:05', event: 'ENCRYPTION_KEY_ROTATED', node: 'SEC-A1' },
    { time: '14:18:22', event: 'UNAUTHORIZED_ACCESS_BLOCKED', node: 'GATEWAY-04' },
    { time: '14:15:10', event: 'NEW_ASSET_INGESTED', node: 'STORAGE-B' },
  ];
}
