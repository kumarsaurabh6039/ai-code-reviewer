import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Dashboard, SEVERITIES } from '../../shared/models/models';
import { ApiService } from '../../shared/services/api.service';
import { ScoreComponent } from '../../shared/components/score-badge.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, DatePipe, ScoreComponent],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Dashboard</h1><span class="muted">Where your projects stand right now</span></div>
        <a class="btn primary" routerLink="/repositories/upload">Add repository</a>
      </div>
      @if (data(); as d) {
        @if (d.repositories === 0) {
          <div class="panel empty">
            <h2>No projects yet</h2>
            <p class="muted">Upload a ZIP or paste a public GitHub URL to get your first review.</p>
            <a class="btn primary" routerLink="/repositories/upload">Add repository</a>
          </div>
        } @else {
          <div class="panel summary">
            <div class="avg">
              @if (d.average_score !== null) { <app-score [v]="d.average_score" /> } @else { <span>-</span> }
              <small class="muted">average score</small>
            </div>
            <div class="vsep"></div>
            <div class="counts">
              @for (s of sevs; track s) {
                <div><span class="sev" [class]="s">{{ s }}</span><b>{{ d.open_issues[s] }}</b></div>
              }
            </div>
            <div class="vsep"></div>
            <div class="avg"><span>{{ d.repositories }}</span><small class="muted">{{ d.repositories === 1 ? 'repository' : 'repositories' }}</small></div>
          </div>
          <div class="section">
            <h2>Recent analyses</h2>
            <div class="list">
              @for (r of d.recent; track r.id) {
                <a class="row recent" [routerLink]="['/analysis', r.id]">
                  <b>{{ r.repository_name }}</b>
                  <span class="muted">{{ r.created_at | date:'medium' }}</span>
                  <span class="chip">{{ r.status }}</span>
                  <span>@if (r.overall_score !== null) { <app-score [v]="r.overall_score" /> }</span>
                </a>
              }
            </div>
          </div>
        }
      } @else if (error()) { <div class="error">{{ error() }}</div> } @else { <p class="muted">Loading...</p> }
    </div>
  `,
  styles: [`
    .summary { display: flex; align-items: center; padding: 22px 26px; gap: 30px; flex-wrap: wrap; }
    .avg { display: flex; flex-direction: column; } .avg > span { font-size: 42px; font-weight: 700; line-height: 1; }
    .vsep { width: 1px; align-self: stretch; background: var(--line); }
    .counts { display: flex; gap: 30px; flex-wrap: wrap; } .counts > div { display: flex; flex-direction: column; }
    .counts b { font-size: 26px; line-height: 1.2; }
    .recent { grid-template-columns: 1fr 190px 100px 50px; }
    @media (max-width: 700px) { .recent { grid-template-columns: 1fr auto; } .recent span.muted { display: none; } .vsep { display: none; } }
  `],
})
export class DashboardComponent implements OnInit {
  private api = inject(ApiService);
  data = signal<Dashboard | null>(null); error = signal('');
  sevs = SEVERITIES;
  ngOnInit() { this.api.dashboard().subscribe({ next: d => this.data.set(d), error: () => this.error.set('Could not load the dashboard. Is the backend running?') }); }
}
