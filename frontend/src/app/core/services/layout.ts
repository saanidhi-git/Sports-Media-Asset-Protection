import { Injectable, signal, effect } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class LayoutService {
  private readonly STORAGE_KEY = 'shield_media_sidebar_collapsed';
  
  public readonly isCollapsed = signal<boolean>(this.loadState());

  constructor() {
    // Persist state changes to localStorage
    effect(() => {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.isCollapsed()));
    });
  }

  toggleSidebar() {
    this.isCollapsed.update(state => !state);
  }

  private loadState(): boolean {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    return saved ? JSON.parse(saved) : false;
  }
}
