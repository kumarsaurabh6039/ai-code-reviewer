import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Repo, SEVERITIES } from '../../shared/models/models';
import { ApiService } from '../../shared/services/api.service';
import { ScoreComponent } from '../../shared/components/score-badge.component';

@Component({
  selector: 'app-repositories',
  standalone: true,
  imports: [RouterLink, ScoreComponent],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Repositories</h1><span class="muted">Every project you have analyzed</span></div>
        <a class="btn primary" routerLink="/repositories/upload">Add repository</a>
      </div>
      @if (loaded() && repos().length === 0) {
        <div class="panel empty"><h2>Nothing here yet</h2><p class="muted">Add a ZIP or a GitHub URL to start.</p></div>
      }
      <div class="list">
        @for (r of repos(); track r.id) {
          <div class="row line">
            <div>
              <b>{{ r.name }}</b>
              <div class="muted small">{{ r.source === 'github' ? 'GitHub' : 'ZIP upload' }}@if (r.language) { , mainly {{ r.language }} }</div>
            </div>
            <div class="sevs">
              @for (s of sevs; track s) { @if (r.issue_counts[s]) { <span class="sev" [class]="s">{{ r.issue_counts[s] }} {{ s }}</span> } }
              @if (r.latest_status === 'running' || r.latest_status === 'pending') { <span class="chip">analyzing...</span> }
              @if (r.latest_status === 'failed') { <span class="chip">last run failed</span> }
            </div>
            <div class="score">@if (r.scores.overall !== null) { <app-score [v]="r.scores.overall" /> }</div>
            <div class="acts">
              @if (r.latest_analysis_id) { <a class="btn small" [routerLink]="['/analysis', r.latest_analysis_id]">Report</a> }
              <a class="btn small" [routerLink]="['/mentor', r.id]">Ask mentor</a>
              <button class="btn small danger" (click)="remove(r)">Delete</button>
            </div>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .line { grid-template-columns: 1.4fr 1.4fr 50px auto; } .small { font-size: 13px; }
    .sevs { display: flex; gap: 12px; flex-wrap: wrap; } .acts { display: flex; gap: 6px; }
    @media (max-width: 900px) { .line { grid-template-columns: 1fr auto; } .sevs, .acts { grid-column: 1 / -1; } }
  `],
})
export class RepositoriesComponent implements OnInit {
  private api = inject(ApiService);
  repos = signal<Repo[]>([]); loaded = signal(false); sevs = SEVERITIES;
  ngOnInit() { this.load(); }
  load() { this.api.repos().subscribe(r => { this.repos.set(r); this.loaded.set(true); }); }
  remove(r: Repo) {
    if (confirm(`Delete "${r.name}" and all its analyses? This cannot be undone.`)) this.api.deleteRepo(r.id).subscribe(() => this.load());
  }
}
