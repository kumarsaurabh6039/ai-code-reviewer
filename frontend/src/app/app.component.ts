import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    @if (auth.isLoggedIn()) {
      <div class="shell">
        <nav class="side" aria-label="Main">
          <a class="brand" routerLink="/dashboard">Reviewer</a>
          <a routerLink="/dashboard" routerLinkActive="on">Dashboard</a>
          <a routerLink="/repositories" routerLinkActive="on" [routerLinkActiveOptions]="{exact: true}">Repositories</a>
          <a routerLink="/repositories/upload" routerLinkActive="on">Add repository</a>
          <div class="who">
            <span class="muted">{{ auth.email() }}</span>
            <button class="btn small" (click)="auth.logout()">Log out</button>
          </div>
        </nav>
        <main><router-outlet /></main>
      </div>
    } @else {
      <router-outlet />
    }
  `,
  styles: [`
    .shell { display: grid; grid-template-columns: 210px 1fr; min-height: 100vh; }
    .side { background: #16202a; color: #dfe6ec; padding: 22px 14px; display: flex; flex-direction: column; gap: 4px; position: sticky; top: 0; height: 100vh; }
    .side a { color: #c3ced8; text-decoration: none; padding: 8px 10px; border-radius: 5px; font-weight: 500; }
    .side a:hover { background: #22303c; }
    .side a.on { background: #0f766e; color: #fff; }
    .brand { font-size: 20px; font-weight: 700; color: #fff !important; letter-spacing: -0.02em; margin-bottom: 18px; padding-left: 10px !important; }
    .who { margin-top: auto; display: flex; flex-direction: column; gap: 8px; font-size: 13px; padding: 0 6px; }
    .who .muted { color: #93a2af; overflow-wrap: anywhere; }
    main { min-width: 0; }
    @media (max-width: 760px) {
      .shell { grid-template-columns: 1fr; }
      .side { position: static; height: auto; flex-direction: row; flex-wrap: wrap; align-items: center; }
      .brand { margin: 0 12px 0 0; } .who { margin: 0 0 0 auto; flex-direction: row; align-items: center; }
    }
  `],
})
export class AppComponent {
  auth = inject(AuthService);
}
