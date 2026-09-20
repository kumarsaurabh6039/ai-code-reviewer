import { Component, ElementRef, OnInit, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ChatMsg } from '../../shared/models/models';
import { renderMarkdown } from '../../shared/markdown';
import { ApiService } from '../../shared/services/api.service';

@Component({
  selector: 'app-mentor',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>AI mentor</h1><span class="muted">Answers come from your uploaded code, not generic advice</span></div>
        @if (msgs().length) { <button class="btn small" (click)="clear()">Clear chat</button> }
      </div>
      <div class="cols">
        <section class="panel chat">
          <div class="log" #log>
            @if (!msgs().length && !busy()) {
              <div class="empty">
                <p class="muted">Ask anything about this project.</p>
                <div class="ideas">
                  @for (q of ideas; track q) { <button class="btn small" (click)="ask(q)">{{ q }}</button> }
                </div>
              </div>
            }
            @for (m of msgs(); track $index) {
              <div class="msg" [class.me]="m.role === 'user'">
                @if (m.role === 'user') { <p>{{ m.content }}</p> } @else { <div [innerHTML]="md(m.content)"></div> }
                @if (m.sources?.length) {
                  <div class="src">@for (s of m.sources; track $index) { <span class="chip mono">{{ s.file }}:{{ s.start_line }}-{{ s.end_line }}</span> }</div>
                }
              </div>
            }
            @if (busy()) { <div class="msg"><span class="muted">Reading your code...</span></div> }
          </div>
          <form class="send" (ngSubmit)="ask(text)">
            <input name="q" [(ngModel)]="text" placeholder="Why is my authentication architecture weak?" [disabled]="busy()" aria-label="Your question">
            <button class="btn primary" type="submit" [disabled]="busy() || !text.trim()">Send</button>
          </form>
        </section>

        <aside class="panel pad explain">
          <h2>Explain this code</h2>
          <label class="field">File
            <select [(ngModel)]="file" name="file"><option value="">Choose a file</option>@for (f of files(); track f) { <option [value]="f">{{ f }}</option> }</select>
          </label>
          <div class="range">
            <label class="field">From line<input type="number" min="1" [(ngModel)]="from" name="from"></label>
            <label class="field">To line<input type="number" min="1" [(ngModel)]="to" name="to"></label>
          </div>
          <button class="btn" [disabled]="!file || exBusy()" (click)="explain()">{{ exBusy() ? 'Explaining...' : 'Explain' }}</button>
          @if (exError()) { <div class="error" style="margin-top:12px">{{ exError() }}</div> }
          @if (exText()) { <div class="answer" [innerHTML]="md(exText())"></div> }
        </aside>
      </div>
    </div>
  `,
  styles: [`
    .cols { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; align-items: start; }
    .chat { display: flex; flex-direction: column; height: calc(100vh - 190px); min-height: 420px; }
    .log { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 14px; }
    .msg { max-width: 92%; } .msg.me { align-self: flex-end; background: var(--brand-soft); padding: 8px 14px; border-radius: 6px; } .msg p { margin: 0; }
    .msg ::ng-deep pre.code { background: #16202a; color: #e2e8ee; padding: 12px; border-radius: 5px; overflow-x: auto; font: 13px/1.6 var(--mono); margin: 8px 0; }
    .msg ::ng-deep code { background: #edf0f2; padding: 1px 5px; border-radius: 3px; font: 13px var(--mono); }
    .src { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .send { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--line); }
    .ideas { display: flex; flex-direction: column; gap: 8px; align-items: center; }
    .range { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; } .answer { margin-top: 16px; font-size: 14px; }
    .answer ::ng-deep pre.code { background: #16202a; color: #e2e8ee; padding: 10px; border-radius: 5px; overflow-x: auto; font: 12px/1.6 var(--mono); }
    @media (max-width: 900px) { .cols { grid-template-columns: 1fr; } .chat { height: 70vh; } }
  `],
})
export class MentorComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  @ViewChild('log') logEl?: ElementRef<HTMLElement>;
  repoId = 0; msgs = signal<ChatMsg[]>([]); busy = signal(false); files = signal<string[]>([]);
  text = ''; file = ''; from = 1; to = 40;
  exText = signal(''); exBusy = signal(false); exError = signal('');
  ideas = ['Why is my authentication architecture weak?', 'Which parts of this project are most risky?', 'Where should I add tests first?'];
  md = renderMarkdown;

  ngOnInit() {
    this.repoId = Number(this.route.snapshot.paramMap.get('repoId'));
    this.api.messages(this.repoId).subscribe(m => { this.msgs.set(m); this.scroll(); });
    this.api.files(this.repoId).subscribe(f => this.files.set(f));
  }
  ask(q: string) {
    q = q.trim(); if (!q || this.busy()) return;
    this.text = ''; this.busy.set(true);
    this.msgs.update(m => [...m, { role: 'user', content: q }]); this.scroll();
    this.api.chat(this.repoId, q).subscribe({
      next: r => { this.msgs.update(m => [...m, r]); this.busy.set(false); this.scroll(); },
      error: () => { this.msgs.update(m => [...m, { role: 'assistant', content: 'Something went wrong. Please try again.' }]); this.busy.set(false); },
    });
  }
  clear() { this.api.clearChat(this.repoId).subscribe(() => this.msgs.set([])); }
  explain() {
    this.exBusy.set(true); this.exError.set(''); this.exText.set('');
    this.api.explainCode(this.repoId, this.file, this.from, Math.max(this.to, this.from)).subscribe({
      next: r => { this.exText.set(r.explanation); this.exBusy.set(false); },
      error: e => { this.exError.set(e.error?.detail ?? 'Could not explain that code.'); this.exBusy.set(false); },
    });
  }
  private scroll() { setTimeout(() => { const el = this.logEl?.nativeElement; if (el) el.scrollTop = el.scrollHeight; }); }
}
