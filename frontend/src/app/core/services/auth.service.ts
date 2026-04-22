import { Injectable, signal, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

export interface Token {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
  operator_id: string;
  operating_system: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  
  // Reactive state for the current token and user
  private readonly token = signal<string | null>(localStorage.getItem('access_token'));
  readonly currentUser = signal<User | null>(null);

  isAuthenticated() {
    return !!this.token();
  }

  getToken() {
    return this.token();
  }

  login(email: string, password: string): Observable<Token> {
    // OAuth2 password flow expects x-www-form-urlencoded
    const body = new HttpParams()
      .set('username', email)
      .set('password', password);

    return this.http.post<Token>('/api/login/access-token', body.toString(), {
      headers: new HttpHeaders().set('Content-Type', 'application/x-www-form-urlencoded')
    }).pipe(
      tap(response => {
        this.setToken(response.access_token);
      })
    );
  }

  getMe(): Observable<User> {
    return this.http.get<User>('/api/users/me').pipe(
      tap(user => this.currentUser.set(user))
    );
  }

  register(email: string, password: string): Observable<User> {
    // Mock operator ID generation for now
    const operatorId = `JH-${Math.floor(1000 + Math.random() * 9000)}`;
    const os = (window.navigator as any).userAgentData?.platform || window.navigator.platform;

    return this.http.post<User>('/api/users/register', {
      email,
      password,
      operator_id: operatorId,
      operating_system: os
    });
  }

  logout() {
    localStorage.removeItem('access_token');
    this.token.set(null);
    this.currentUser.set(null);
    this.router.navigate(['/']);
  }

  private setToken(token: string) {
    localStorage.setItem('access_token', token);
    this.token.set(token);
  }
}
