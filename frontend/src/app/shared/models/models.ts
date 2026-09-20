export type Severity = 'critical' | 'high' | 'medium' | 'low';
export const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low'];

export interface Scores {
  overall: number | null; code_quality: number | null; security: number | null;
  performance: number | null; architecture: number | null; testing: number | null; documentation: number | null;
}
export type IssueCounts = Record<Severity, number>;

export interface Repo {
  id: number; name: string; source: 'zip' | 'github'; github_url: string | null; branch: string | null;
  language: string | null; created_at: string; latest_analysis_id: number | null; latest_status: string | null;
  scores: Scores; issue_counts: Partial<IssueCounts>;
}
export interface RoadmapItem { priority: number; title: string; category: string; effort: string; issue_ids: number[]; why: string; }
export interface Analysis {
  id: number; repository_id: number; repository_name: string; status: 'pending' | 'running' | 'completed' | 'failed';
  stage: string | null; error: string | null; commit_sha: string | null; used_ai: boolean; scores: Scores;
  metrics: Record<string, any> | null; languages: Record<string, number> | null; summary: string | null;
  roadmap: RoadmapItem[] | null; issue_counts: IssueCounts; created_at: string; finished_at: string | null;
}
export interface Issue {
  id: number; analysis_id: number; file_path: string; line_number: number; end_line: number | null;
  severity: Severity; category: string; title: string; description: string; suggestion: string;
  fix_before: string | null; fix_after: string | null; explanation: string | null; rule_id: string | null;
  source: 'static' | 'ai'; confidence: number; status: 'open' | 'resolved' | 'ignored';
}
export interface CodeView { file_path: string; start_line: number; highlight_start: number; highlight_end: number; lines: string[]; }
export interface Explain { explanation: string; why_it_matters: string; before: string; after: string; ai: boolean; }
export interface ChatSource { file: string; start_line: number; end_line: number; }
export interface ChatMsg { id?: number; role: 'user' | 'assistant'; content: string; sources?: ChatSource[]; }
export interface Dashboard {
  repositories: number; average_score: number | null; open_issues: IssueCounts;
  recent: { id: number; repository_id: number; repository_name: string; status: string; overall_score: number | null; created_at: string }[];
}
export const CATEGORY_LABEL: Record<string, string> = {
  bug: 'Bug', security: 'Security', code_smell: 'Code smell', duplication: 'Duplication',
  performance: 'Performance', architecture: 'Architecture', testing: 'Testing', documentation: 'Documentation',
};
