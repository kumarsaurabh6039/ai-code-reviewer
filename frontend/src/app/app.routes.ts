import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login.component').then(m => m.LoginComponent) },
  { path: 'dashboard', canActivate: [authGuard], loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent) },
  { path: 'repositories', canActivate: [authGuard], loadComponent: () => import('./features/repositories/repositories.component').then(m => m.RepositoriesComponent) },
  { path: 'repositories/upload', canActivate: [authGuard], loadComponent: () => import('./features/repositories/upload.component').then(m => m.UploadComponent) },
  { path: 'analysis/:id', canActivate: [authGuard], loadComponent: () => import('./features/analysis/analysis.component').then(m => m.AnalysisComponent) },
  { path: 'issues/:id', canActivate: [authGuard], loadComponent: () => import('./features/issues/issue-detail.component').then(m => m.IssueDetailComponent) },
  { path: 'mentor/:repoId', canActivate: [authGuard], loadComponent: () => import('./features/mentor/mentor.component').then(m => m.MentorComponent) },
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  { path: '**', redirectTo: 'dashboard' },
];
