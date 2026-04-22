import { Component, signal, inject, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  protected readonly title = signal('frontend');
  protected readonly message = signal('Loading...');
  private readonly http = inject(HttpClient);

  ngOnInit() {
    this.http.get<{ message: string }>('/api/').subscribe({
      next: (response) => this.message.set(response.message),
      error: (err) => {
        console.error('Error fetching from backend:', err);
        this.message.set('Failed to connect to FastAPI');
      }
    });
  }
}
