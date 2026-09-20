import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-score',
  standalone: true,
  template: `<span class="s" [class.good]="v >= 80" [class.warn]="v >= 60 && v < 80" [class.bad]="v < 60">{{ v }}</span>`,
  styles: [`.s { font-weight: 700; font-variant-numeric: tabular-nums; } .good { color: var(--good); } .warn { color: var(--warn); } .bad { color: var(--bad); }`],
})
export class ScoreComponent { @Input({ required: true }) v = 0; }
