import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { tap } from 'rxjs';
import { API_URL } from '../config';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  // NOTE: localStorage is simple but readable by injected scripts. Fine for an MVP; consider httpOnly cookies later.
  readonly token = signal<string | null>(localStorage.getItem('token'));
  readonly email = signal<string | null>(localStorage.getItem('email'));
  readonly isLoggedIn = computed(() => !!this.token());

  login(email: string, password: string) {
    return this.http.post<{ access_token: string }>(`${API_URL}/auth/login`, { email, password })
      .pipe(tap(t => this.save(t.access_token, email)));
  }
  register(email: string, password: string) {
    return this.http.post<{ access_token: string }>(`${API_URL}/auth/register`, { email, password })
      .pipe(tap(t => this.save(t.access_token, email)));
  }
  logout() {
    localStorage.removeItem('token'); localStorage.removeItem('email');
    this.token.set(null); this.email.set(null);
    this.router.navigate(['/login']);
  }
  private save(token: string, email: string) {
    localStorage.setItem('token', token); localStorage.setItem('email', email);
    this.token.set(token); this.email.set(email);
  }
}
