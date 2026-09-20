import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="wrap">
      <section class="intro">
        <h1>Reviewer</h1>
        <p class="lead">Upload a codebase and get bugs, security issues, test gaps and a prioritized fix roadmap, with an AI mentor that answers questions about your own code.</p>
        <pre class="peek" aria-hidden="true"><span class="ln">87</span>  token = decode(token)
<span class="ln">88</span>  <span class="flag">high · JWT expiration is not validated</span></pre>
      </section>
      <form class="panel pad form" (ngSubmit)="submit()">
        <h2>{{ mode() === 'login' ? 'Log in' : 'Create your account' }}</h2>
        @if (error()) { <div class="error" role="alert">{{ error() }}</div> }
        <label class="field">Email<input type="email" name="email" [(ngModel)]="email" required autocomplete="email"></label>
        <label class="field">Password<input type="password" name="password" [(ngModel)]="password" required minlength="8" autocomplete="current-password"></label>
        <button class="btn primary" type="submit" [disabled]="busy()">{{ mode() === 'login' ? 'Log in' : 'Create account' }}</button>
        <p class="switch muted">
          @if (mode() === 'login') { New here? <a href="#" (click)="toggle($event)">Create an account</a> }
          @else { Already registered? <a href="#" (click)="toggle($event)">Log in</a> }
        </p>
      </form>
    </div>
  `,
  styles: [`
    .wrap { min-height: 100vh; display: grid; grid-template-columns: 1.1fr 1fr; gap: 56px; align-items: center; max-width: 1000px; margin: 0 auto; padding: 32px; }
    .lead { font-size: 18px; color: var(--muted); max-width: 46ch; }
    h1 { font-size: 44px; letter-spacing: -0.03em; }
    .peek { background: #16202a; color: #dfe6ec; padding: 16px 18px; border-radius: 6px; font: 13px/1.7 var(--mono); margin-top: 28px; max-width: 420px; }
    .ln { color: #6b7c8a; margin-right: 8px; } .flag { color: #f2a36b; }
    .form { max-width: 380px; width: 100%; justify-self: end; }
    .switch { margin: 14px 0 0; font-size: 14px; }
    @media (max-width: 800px) { .wrap { grid-template-columns: 1fr; gap: 24px; } .form { justify-self: stretch; max-width: none; } h1 { font-size: 34px; } }
  `],
})
export class LoginComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  mode = signal<'login' | 'register'>('login');
  error = signal(''); busy = signal(false);
  email = ''; password = '';

  toggle(e: Event) { e.preventDefault(); this.mode.update(m => (m === 'login' ? 'register' : 'login')); this.error.set(''); }
  submit() {
    this.error.set(''); this.busy.set(true);
    const call = this.mode() === 'login' ? this.auth.login(this.email, this.password) : this.auth.register(this.email, this.password);
    call.subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: e => { this.busy.set(false); this.error.set(typeof e.error?.detail === 'string' ? e.error.detail : 'Could not sign in. Check your details (password needs 8+ characters).'); },
    });
  }
}
