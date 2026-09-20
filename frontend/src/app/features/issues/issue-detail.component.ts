import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CATEGORY_LABEL, CodeView, Explain, Issue } from '../../shared/models/models';
import { ApiService } from '../../shared/services/api.service';

@Component({
  selector: 'app-issue-detail',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="page">
      @if (issue(); as i) {
        <a class="muted" [routerLink]="['/analysis', i.analysis_id]">Back to report</a>
        <div class="head">
          <span class="sev" [class]="i.severity">{{ i.severity }}</span>
          <span class="chip">{{ label(i.category) }}</span>
          <span class="chip">{{ i.source === 'ai' ? 'AI finding' : 'Static analysis' }}</span>
          <span class="chip">confidence {{ (i.confidence * 100).toFixed(0) }}%</span>
        </div>
        <h1>{{ i.title }}</h1>
        <p class="mono loc">{{ i.file_path }}, line {{ i.line_number }}</p>

        <div class="panel pad">
          <h3>Problem</h3><p>{{ i.description }}</p>
          <h3>Suggested fix</h3><p>{{ i.suggestion }}</p>
        </div>

        <div class="tabs" role="tablist">
          <button role="tab" [class.on]="tab() === 'explain'" (click)="openExplain()">Explain</button>
          <button role="tab" [class.on]="tab() === 'fix'" (click)="tab.set('fix')">Suggested fix</button>
          <button role="tab" [class.on]="tab() === 'code'" (click)="tab.set('code')">View code</button>
        </div>

        @if (tab() === 'explain') {
          <div class="panel pad">
            @if (loading()) { <p class="muted">Explaining...</p> }
            @else {
              @if (ex(); as e) {
                <p>{{ e.explanation }}</p>
                @if (e.why_it_matters) { <h3>Why it matters</h3><p>{{ e.why_it_matters }}</p> }
                @if (!e.ai) { <p class="muted small">Add ANTHROPIC_API_KEY to the backend to get a deeper AI explanation.</p> }
              }
            }
          </div>
        }
        @if (tab() === 'fix') {
          <div class="panel pad">
            @if (ex()?.before || i.fix_before) {
              <div class="diff">
                <div><div class="cap">Before</div><pre class="code bad">{{ ex()?.before || i.fix_before }}</pre></div>
                <div><div class="cap">After (example)</div><pre class="code good">{{ ex()?.after || i.fix_after }}</pre></div>
              </div>
            } @else { <p class="muted">No code example for this issue. Follow the suggested fix above.</p> }
            <p class="muted small">Suggestions are never applied automatically. Review them before changing your code.</p>
          </div>
        }
        @if (tab() === 'code') {
          <div class="panel codebox">
            @if (code(); as c) {
              <div class="cap pad-s mono">{{ c.file_path }}</div>
              @for (l of c.lines; track $index) {
                <div class="ln" [class.hl]="c.start_line + $index >= c.highlight_start && c.start_line + $index <= c.highlight_end">
                  <span class="num">{{ c.start_line + $index }}</span><span class="src">{{ l }}</span>
                </div>
              }
            } @else { <p class="pad-s muted">Loading code...</p> }
          </div>
        }

        <div class="acts">
          @if (i.status === 'open') {
            <button class="btn" (click)="setStatus('resolved')">Mark as resolved</button>
            <button class="btn" (click)="setStatus('ignored')">Ignore</button>
          } @else { <span class="chip">{{ i.status }}</span><button class="btn" (click)="setStatus('open')">Reopen</button> }
        </div>
      } @else { <p class="muted">Loading...</p> }
    </div>
  `,
  styles: [`
    .head { display: flex; gap: 8px; align-items: center; margin: 14px 0 8px; flex-wrap: wrap; } .loc { margin: 0 0 18px; color: var(--muted); }
    .small { font-size: 13px; }
    .tabs { display: flex; gap: 4px; margin: 22px 0 10px; border-bottom: 1px solid var(--line); }
    .tabs button { font: inherit; font-weight: 600; background: none; border: 0; border-bottom: 3px solid transparent; padding: 8px 14px; cursor: pointer; color: var(--muted); }
    .tabs button.on { color: var(--ink); border-bottom-color: var(--brand); }
    .diff { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; } .cap { font-weight: 600; font-size: 13px; margin-bottom: 6px; }
    pre.code { margin: 0; padding: 12px; border-radius: 5px; font: 13px/1.6 var(--mono); overflow-x: auto; white-space: pre-wrap; word-break: break-word; }
    pre.bad { background: #fdf0ee; border-left: 3px solid var(--crit); } pre.good { background: #e8f5f2; border-left: 3px solid var(--good); }
    .codebox { overflow: hidden; font: 13px/1.65 var(--mono); } .pad-s { padding: 8px 14px; border-bottom: 1px solid var(--line); background: #f7f9fa; margin: 0; }
    .ln { display: flex; } .ln.hl { background: #fff3d6; box-shadow: inset 3px 0 0 var(--high); }
    .num { width: 52px; text-align: right; padding-right: 12px; color: #98a3ad; user-select: none; flex: none; } .src { white-space: pre; overflow-x: auto; }
    .acts { margin-top: 20px; display: flex; gap: 8px; align-items: center; }
    @media (max-width: 700px) { .diff { grid-template-columns: 1fr; } }
  `],
})
export class IssueDetailComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  issue = signal<Issue | null>(null); code = signal<CodeView | null>(null); ex = signal<Explain | null>(null);
  tab = signal<'explain' | 'fix' | 'code'>('code'); loading = signal(false);
  label = (k: string) => CATEGORY_LABEL[k] ?? k;

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.api.issue(id).subscribe(i => this.issue.set(i));
    this.api.issueCode(id).subscribe(c => this.code.set(c));
  }
  openExplain() {
    this.tab.set('explain');
    if (this.ex()) return;
    this.loading.set(true);
    this.api.explainIssue(this.issue()!.id).subscribe({ next: e => { this.ex.set(e); this.loading.set(false); }, error: () => this.loading.set(false) });
  }
  setStatus(s: string) { this.api.setIssueStatus(this.issue()!.id, s).subscribe(i => this.issue.set(i)); }
}
