# Architecture

```
Angular UI  --REST/JWT-->  FastAPI  --> SQLAlchemy --> SQLite / PostgreSQL
                             |--> analyzers/ (AST, regex rules, duplicates, architecture, tests, docs, Bandit)
                             |--> services/analysis_service.py (pipeline, runs in a background task)
                             |--> ai/ (Claude client, prompts, BM25 retriever)
```

## Pipeline (services/analysis_service.py)
1. Prepare repo (ZIP already extracted safely, or shallow git clone).
2. scan_repository: ignore .git, node_modules, venv, dist, build, .env; skip binary/huge files; detect language, LOC, tests.
3. Static analysis: Python AST (complexity, long functions, nesting, mutable defaults, bare except, N+1 patterns, unreachable code),
   regex security rules (secrets, SQLi, XSS, eval, weak hash, TLS off, JWT validation off, CORS, debug), Bandit, duplicate blocks,
   circular imports, layering, missing tests, README/dependency/.gitignore checks.
   Tests, docs and example folders are treated as non-production and produce far fewer findings.
4. Chunk code (60 lines, 10 overlap) into code_chunks for the mentor.
5. AI review (optional): the riskiest files (static findings + path keywords such as auth/payment/db) are sent to Claude.
   Each returned issue is validated against the real file (line exists, valid severity/category).
6. De-duplicate and cap findings, save issues.
7. Score: penalty per issue (critical 15, high 8, medium 3, low 1, times confidence) divided by sqrt(KLOC), plus caps for
   test ratio and documentation. Overall = weighted average.
8. Roadmap: grouped issues ranked by severity then category (security first); Claude refines it when available.

## RAG (mentor)
Question -> BM25 search over chunks (path tokens boosted, prefix matching, tests demoted) -> top 6 chunks + top issues
-> Claude answers using only those excerpts and cites file:lines.
To upgrade to embeddings: add a pgvector column to code_chunks, embed in step 4, and replace ai/retriever.py.

## Security notes
- Zip-slip / absolute paths / symlinks rejected; real bytes counted while extracting (zip-bomb protection).
- GitHub URLs must match https://github.com/owner/repo; branch names validated; hooks disabled; .git removed.
- Code is never executed. Bandit only parses.
- Ownership checks on every repository/analysis/issue endpoint.
- Repo content is passed to the LLM as untrusted data inside tags.
