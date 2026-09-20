# Database

Tables are created automatically on startup (use Alembic for production migrations):

- users (id, email, password_hash, created_at)
- repositories (id, user_id, name, source, github_url, branch, language, local_path, commit_sha, created_at)
- analyses (id, repository_id, status, stage, error, commit_sha, used_ai, six scores + overall, metrics, languages,
  summary, roadmap, created_at, finished_at)
- issues (id, analysis_id, file_path, line_number, end_line, severity, category, title, description, suggestion,
  fix_before, fix_after, explanation, rule_id, source static|ai, confidence, status open|resolved|ignored)
- code_chunks (id, repository_id, file_path, start_line, end_line, language, content)
- chat_messages (id, repository_id, role, content, sources, created_at)

The reports table from the original plan is folded into analyses (summary, roadmap); reports are generated on demand.
