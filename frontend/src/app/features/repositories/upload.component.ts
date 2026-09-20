import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../shared/services/api.service';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="page narrow">
      <h1>Add a repository</h1>
      <p class="muted">Code is only read and parsed. It is never executed.</p>
      <div class="tabs" role="tablist">
        <button role="tab" [attr.aria-selected]="tab() === 'zip'" [class.on]="tab() === 'zip'" (click)="tab.set('zip')">Upload ZIP</button>
        <button role="tab" [attr.aria-selected]="tab() === 'github'" [class.on]="tab() === 'github'" (click)="tab.set('github')">GitHub URL</button>
      </div>
      <div class="panel pad">
        @if (error()) { <div class="error" role="alert">{{ error() }}</div> }
        @if (tab() === 'zip') {
          <label class="drop" [class.over]="over()" (dragover)="$event.preventDefault(); over.set(true)" (dragleave)="over.set(false)" (drop)="onDrop($event)">
            <input type="file" accept=".zip" (change)="onPick($event)" hidden>
            @if (file()) { <b>{{ file()!.name }}</b><span class="muted">{{ (file()!.size / 1048576).toFixed(1) }} MB. Click to choose another.</span> }
            @else { <b>Drop a .zip here or click to choose</b><span class="muted">Up to 50 MB. node_modules, .git, venv and .env are skipped automatically.</span> }
          </label>
          <button class="btn primary" [disabled]="!file() || busy()" (click)="sendZip()">{{ busy() ? 'Uploading...' : 'Upload and analyze' }}</button>
        } @else {
          <label class="field">Public repository URL<input [(ngModel)]="url" name="url" placeholder="https://github.com/owner/repo"></label>
          <label class="field">Branch (optional)<input [(ngModel)]="branch" name="branch" placeholder="default branch"></label>
          <button class="btn primary" [disabled]="!url.trim() || busy()" (click)="sendGithub()">{{ busy() ? 'Starting...' : 'Clone and analyze' }}</button>
        }
      </div>
      <p class="muted hint">Supported: Python, JavaScript, TypeScript, HTML, CSS, JSON, SQL.</p>
    </div>
  `,
  styles: [`
    .narrow { max-width: 640px; }
    .tabs { display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; margin: 14px 0 16px; background: #fff; }
    .tabs button { font: inherit; font-weight: 600; border: 0; background: transparent; padding: 8px 18px; cursor: pointer; color: var(--muted); }
    .tabs button.on { background: var(--brand); color: #fff; }
    .drop { display: flex; flex-direction: column; gap: 4px; align-items: center; text-align: center; padding: 38px 20px; border: 2px dashed var(--line); border-radius: 6px; cursor: pointer; margin-bottom: 16px; }
    .drop.over, .drop:hover { border-color: var(--brand); background: var(--brand-soft); }
    .hint { font-size: 13px; margin-top: 12px; }
  `],
})
export class UploadComponent {
  private api = inject(ApiService);
  private router = inject(Router);
  tab = signal<'zip' | 'github'>('zip'); file = signal<File | null>(null);
  busy = signal(false); error = signal(''); over = signal(false);
  url = ''; branch = '';

  onPick(e: Event) { const f = (e.target as HTMLInputElement).files?.[0]; if (f) this.file.set(f); }
  onDrop(e: DragEvent) { e.preventDefault(); this.over.set(false); const f = e.dataTransfer?.files?.[0]; if (f) this.file.set(f); }
  sendZip() { this.run(this.api.uploadZip(this.file()!)); }
  sendGithub() { this.run(this.api.addGithub(this.url.trim(), this.branch.trim() || null)); }
  private run(obs: ReturnType<ApiService['uploadZip']>) {
    this.error.set(''); this.busy.set(true);
    obs.subscribe({
      next: r => this.router.navigate(['/analysis', r.analysis_id]),
      error: e => { this.busy.set(false); this.error.set(typeof e.error?.detail === 'string' ? e.error.detail : 'Upload failed. Please try again.'); },
    });
  }
}
