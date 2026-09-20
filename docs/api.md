# API (all under /api, JWT bearer token except register/login)

- POST /auth/register, /auth/login -> {access_token};  GET /auth/me
- GET /dashboard
- GET /repositories;  DELETE /repositories/{id}
- POST /repositories/zip (multipart "file") -> 202 {repository_id, analysis_id}
- POST /repositories/github {url, branch?} -> 202
- POST /repositories/{id}/analyze (re-analyze);  GET /repositories/{id}/analyses
- GET /analyses/{id} (poll while status is pending/running)
- GET /analyses/{id}/issues (filters: severity, category, status)
- GET /analyses/{id}/report?format=md|json
- GET /issues/{id};  PATCH /issues/{id} {status};  GET /issues/{id}/code;  POST /issues/{id}/explain
- GET /mentor/{repoId}/messages;  POST /mentor/{repoId}/chat {message};  DELETE /mentor/{repoId}/messages
- GET /mentor/{repoId}/files;  POST /mentor/{repoId}/explain-code {file_path, start_line, end_line}

Interactive docs: http://localhost:8000/docs
