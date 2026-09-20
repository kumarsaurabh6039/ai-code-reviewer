import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from '../../core/config';
import { Analysis, ChatMsg, CodeView, Dashboard, Explain, Issue, Repo } from '../models/models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private u = (p: string) => `${API_URL}${p}`;

  dashboard() { return this.http.get<Dashboard>(this.u('/dashboard')); }
  repos() { return this.http.get<Repo[]>(this.u('/repositories')); }
  deleteRepo(id: number) { return this.http.delete(this.u(`/repositories/${id}`)); }
  uploadZip(file: File) {
    const fd = new FormData(); fd.append('file', file);
    return this.http.post<{ repository_id: number; analysis_id: number }>(this.u('/repositories/zip'), fd);
  }
  addGithub(url: string, branch: string | null) {
    return this.http.post<{ repository_id: number; analysis_id: number }>(this.u('/repositories/github'), { url, branch: branch || null });
  }
  reanalyze(repoId: number) {
    return this.http.post<{ repository_id: number; analysis_id: number }>(this.u(`/repositories/${repoId}/analyze`), {});
  }
  analysis(id: number) { return this.http.get<Analysis>(this.u(`/analyses/${id}`)); }
  issues(analysisId: number) { return this.http.get<Issue[]>(this.u(`/analyses/${analysisId}/issues`)); }
  report(analysisId: number, format: 'md' | 'json') {
    return this.http.get(this.u(`/analyses/${analysisId}/report`), { params: new HttpParams().set('format', format), responseType: 'blob' });
  }
  issue(id: number) { return this.http.get<Issue>(this.u(`/issues/${id}`)); }
  setIssueStatus(id: number, status: string) { return this.http.patch<Issue>(this.u(`/issues/${id}`), { status }); }
  issueCode(id: number) { return this.http.get<CodeView>(this.u(`/issues/${id}/code`)); }
  explainIssue(id: number) { return this.http.post<Explain>(this.u(`/issues/${id}/explain`), {}); }
  messages(repoId: number) { return this.http.get<ChatMsg[]>(this.u(`/mentor/${repoId}/messages`)); }
  chat(repoId: number, message: string) { return this.http.post<ChatMsg>(this.u(`/mentor/${repoId}/chat`), { message }); }
  clearChat(repoId: number) { return this.http.delete(this.u(`/mentor/${repoId}/messages`)); }
  files(repoId: number) { return this.http.get<string[]>(this.u(`/mentor/${repoId}/files`)); }
  explainCode(repoId: number, file_path: string, start_line: number, end_line: number) {
    return this.http.post<{ explanation: string }>(this.u(`/mentor/${repoId}/explain-code`), { file_path, start_line, end_line });
  }
}
