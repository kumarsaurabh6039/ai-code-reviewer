import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Analysis, CATEGORY_LABEL, Issue, SEVERITIES, Severity } from '../../shared/models/models';
import { ApiService } from '../../shared/services/api.service';
import { ScoreComponent } from '../../shared/components/score-badge.component';

@Component({
  selector: 'app-analysis',
  standalone: true,
  imports: [RouterLink, ScoreComponent],
  template: `
    <div class="page">
      @if (a(); as a) {
        <div class="page-head">
          <div>
            <h1>{{ a.repository_name }}</h1>
            <span class="muted">Analysis #{{ a.id }}@if (a.commit_sha) {, version <span class="mono">{{ a.commit_sha.slice(0, 10) }}</span>}</span>
          </div>
          <div class="acts">
            <a class="btn primary" [routerLink]="['/mentor', a.repository_id]">Ask AI mentor</a>
            @if (a.status === 'completed' || a.status === 'failed') { <button class="btn" (click)="reanalyze()">Re-analyze</button> }
          </div>
        </div>

        @if (a.status === 'pending' || a.status === 'running') {
          <div class="panel pad">
            <h2>Analyzing your code</h2>
            <p class="muted">{{ a.stage || 'Starting' }}...</p>
            <div class="bar-indeterminate" role="progressbar" aria-label="Analysis in progress"></div>
          </div>
        } @else if (a.status === 'failed') {
          <div class="error" role="alert"><b>Analysis failed.</b> {{ a.error }}</div>
        } @else {
          <div class="top">
            <div class="panel pad score">
              <div class="big"><app-score [v]="a.scores.overall ?? 0" /><span class="of">/100</span></div>
              <div class="muted">Overall health</div>
              <p class="note">
                {{ a.used_ai ? 'AI-assisted opinion' : 'Automated static analysis' }}, calculated with a fixed formula.
                It is a guide for prioritizing work, not an industry certification.
              </p>
            </div>
            <div class="panel pad bars">
              @for (c of cats(); track c.label) {
                <div class="bar-row">
                  <span>{{ c.label }}</span>
                  <div class="track"><div class="fill" [style.width.%]="c.v" [class.good]="c.v >= 80" [class.warn]="c.v >= 60 && c.v < 80" [class.bad]="c.v < 60"></div></div>
                  <app-score [v]="c.v" />
                </div>
              }
            </div>
          </div>

          @if (a.summary) { <p class="summary">{{ a.summary }}</p> }

          <div class="section metrics">
            <div><b>{{ a.metrics?.['files'] }}</b><span class="muted">files</span></div>
            <div><b>{{ a.metrics?.['lines'] }}</b><span class="muted">lines of code</span></div>
            <div><b>{{ a.metrics?.['functions'] }}</b><span class="muted">functions</span></div>
            <div><b>{{ a.metrics?.['classes'] }}</b><span class="muted">classes</span></div>
            <div><b>{{ a.metrics?.['test_files'] }}</b><span class="muted">test files</span></div>
          </div>
          @if (langs().length) {
            <div class="langs" aria-label="Languages">
              @for (l of langs(); track l[0]; let i = $index) { <div [style.flex]="l[1]" [style.background]="colors[i % colors.length]" [title]="l[0] + ' ' + l[1] + '%'"></div> }
            </div>
            <div class="legend">@for (l of langs(); track l[0]; let i = $index) { <span><i [style.background]="colors[i % colors.length]"></i>{{ l[0] }} {{ l[1] }}%</span> }</div>
          }

          <div class="section">
            <h2>Issues found: {{ issues().length }}</h2>
            <div class="filters">
              <button class="btn small" [class.primary]="!sev()" (click)="sev.set(null)">All</button>
              @for (s of sevs; track s) { <button class="btn small" [class.primary]="sev() === s" (click)="sev.set(s)"><span class="sev" [class]="s">{{ a.issue_counts[s] }} {{ s }}</span></button> }
              <select [value]="cat()" (change)="cat.set($any($event.target).value)" aria-label="Filter by category">
                <option value="">All categories</option>
                @for (k of catKeys(); track k) { <option [value]="k">{{ label(k) }}</option> }
              </select>
            </div>
            <div class="list">
              @for (i of filtered(); track i.id) {
                <a class="row issue" [routerLink]="['/issues', i.id]" [class.done]="i.status !== 'open'">
                  <span class="sev" [class]="i.severity">{{ i.severity }}</span>
                  <div><b>{{ i.title }}</b><div class="muted mono">{{ i.file_path }}:{{ i.line_number }}</div></div>
                  <span class="chip">{{ label(i.category) }}</span>
                  @if (i.status !== 'open') { <span class="chip">{{ i.status }}</span> } @else if (i.source === 'ai') { <span class="chip">AI</span> } @else { <span></span> }
                </a>
              } @empty { <div class="empty muted">No issues match this filter.</div> }
            </div>
          </div>

          <div class="section">
            <h2>Your improvement roadmap</h2>
            <ol class="road">
              @for (r of a.roadmap; track r.priority) {
                <li class="panel">
                  <div class="rh"><b>Priority {{ r.priority }}: {{ r.title }}</b></div>
                  <div class="muted">{{ label(r.category) }} · Effort: {{ r.effort }}@if (r.issue_ids.length) { · <a [routerLink]="['/issues', r.issue_ids[0]]">view first issue</a> }</div>
                  @if (r.why) { <p class="why">{{ r.why }}</p> }
                </li>
              }
            </ol>
          </div>

          <div class="section acts">
            <span class="muted">Export report:</span>
            <button class="btn small" (click)="download('md')">Markdown</button>
            <button class="btn small" (click)="download('json')">JSON</button>
          </div>
        }
      } @else if (error()) { <div class="error">{{ error() }}</div> } @else { <p class="muted">Loading...</p> }
    </div>
  `,
  styles: [`
    .acts { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .top { display: grid; grid-template-columns: 300px 1fr; gap: 16px; }
    .big { display: flex; align-items: baseline; gap: 4px; } .big app-score { font-size: 64px; line-height: 1; }
    .big app-score ::ng-deep .s { font-size: 64px; } .of { color: var(--muted); font-size: 20px; }
    .note { font-size: 13px; color: var(--muted); margin: 12px 0 0; }
    .bar-row { display: grid; grid-template-columns: 110px 1fr 34px; gap: 12px; align-items: center; padding: 5px 0; }
    .track { height: 10px; background: #e8ecef; border-radius: 2px; overflow: hidden; } .fill { height: 100%; }
    .fill.good { background: var(--good); } .fill.warn { background: #d1a11a; } .fill.bad { background: var(--bad); }
    .summary { margin: 18px 0 0; max-width: 75ch; }
    .metrics { display: flex; gap: 34px; flex-wrap: wrap; margin-top: 28px; } .metrics div { display: flex; flex-direction: column; } .metrics b { font-size: 24px; line-height: 1.2; }
    .langs { display: flex; height: 10px; border-radius: 2px; overflow: hidden; margin-top: 18px; gap: 2px; }
    .legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; margin-top: 8px; color: var(--muted); } .legend i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; }
    .filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; align-items: center; } .filters select { width: auto; padding: 5px 10px; }
    .issue { grid-template-columns: 90px 1fr auto 60px; } .issue.done { opacity: .55; }
    .road { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; } .road li { padding: 14px 18px; } .why { margin: 6px 0 0; font-size: 14px; }
    @media (max-width: 800px) { .top { grid-template-columns: 1fr; } .issue { grid-template-columns: 1fr auto; } }
  `],
})
export class AnalysisComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  a = signal<Analysis | null>(null); issues = signal<Issue[]>([]); error = signal('');
  sev = signal<Severity | null>(null); cat = signal('');
  sevs = SEVERITIES;
  colors = ['#0f766e', '#2f6fd0', '#c46a1a', '#7a4fb3', '#8a939b', '#b3261e'];
  private timer: any; private id = 0;

  cats = computed(() => {
    const s = this.a()?.scores; if (!s) return [];
    return [['Code quality', s.code_quality], ['Security', s.security], ['Performance', s.performance],
      ['Architecture', s.architecture], ['Testing', s.testing], ['Documentation', s.documentation]]
      .map(([label, v]) => ({ label: label as string, v: (v as number) ?? 0 }));
  });
  langs = computed(() => Object.entries(this.a()?.languages ?? {}) as [string, number][]);
  catKeys = computed(() => [...new Set(this.issues().map(i => i.category))]);
  filtered = computed(() => this.issues().filter(i => (!this.sev() || i.severity === this.sev()) && (!this.cat() || i.category === this.cat())));
  label = (k: string) => CATEGORY_LABEL[k] ?? k;

  ngOnInit() { this.route.paramMap.subscribe(p => { this.id = Number(p.get('id')); this.a.set(null); this.load(); }); }
  ngOnDestroy() { clearTimeout(this.timer); }

  load() {
    clearTimeout(this.timer);
    this.api.analysis(this.id).subscribe({
      next: a => {
        this.a.set(a);
        if (a.status === 'pending' || a.status === 'running') this.timer = setTimeout(() => this.load(), 1500);
        else if (a.status === 'completed') this.api.issues(a.id).subscribe(i => this.issues.set(i));
      },
      error: () => this.error.set('Analysis not found.'),
    });
  }
  reanalyze() { this.api.reanalyze(this.a()!.repository_id).subscribe(r => this.router.navigate(['/analysis', r.analysis_id])); }
  download(fmt: 'md' | 'json') {
    this.api.report(this.id, fmt).subscribe(blob => {
      const url = URL.createObjectURL(blob); const link = document.createElement('a');
      link.href = url; link.download = `report-${this.id}.${fmt}`; link.click(); URL.revokeObjectURL(url);
    });
  }
}
