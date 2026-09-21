# AI Code Reviewer & Developer Mentor

An AI-powered code review platform that analyzes complete codebases, detects bugs, security issues, code smells, duplication, architecture and testing problems, generates a deterministic code health score and improvement roadmap, and provides an AI developer mentor grounded in the user's own code.

Upload a ZIP file or provide a public GitHub repository URL to get an automated codebase review.

---

## 🚀 Live Demo

**Frontend:**  
https://ai-code-reviewer-aarzu.vercel.app

**Backend API:**  
https://ai-code-reviewer-t92y.onrender.com

**API Documentation:**  
https://ai-code-reviewer-t92y.onrender.com/docs

**Health Check:**  
https://ai-code-reviewer-t92y.onrender.com/health

---

## ✨ Features

- 📦 Upload a project as a ZIP file
- 🔗 Analyze public GitHub repositories
- 🐍 Python AST-based analysis
- 🔐 Security vulnerability detection
- 🧹 Code smell detection
- ♻️ Duplicate code detection
- 🏗️ Architecture analysis
- 🧪 Testing readiness checks
- 📚 Documentation checks
- 🤖 AI-powered code review
- 💬 AI Developer Mentor with RAG
- 📊 Deterministic code health score
- 🗺️ Prioritized improvement roadmap
- 🔎 File and line-level issue references
- 🛡️ ZIP-slip, zip-bomb and symlink protection
- 🚫 Uploaded code is never executed
- 🔄 Groq as the primary LLM with Gemini fallback
- ⚙️ Static analysis works even without an AI API key

---

## 🧠 How It Works

```text
                    ZIP / GitHub URL
                           │
                           ▼
                 Safe Extraction / Clone
                           │
                           ▼
                    File Filtering
                           │
                           ▼
                   Language Detection
                           │
                           ▼
                  Static Code Analysis
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         Security      Python AST    Duplicates
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                  Architecture / Tests
                           │
                           ▼
                     Code Chunking
                           │
                           ▼
                  Risk-based AI Review
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                  Groq          Gemini
                Primary        Fallback
                    │             │
                    └──────┬──────┘
                           ▼
                   Issue Validation
                           │
                           ▼
                  Deterministic Scoring
                           │
                           ▼
                    Roadmap + Report
                           │
                           ▼
                     AI Mentor / RAG
```

---

## 🏗️ Architecture

The application follows a **static-first, AI-second** architecture.

### 1. Static Analysis

The project is analyzed using deterministic tools and custom analyzers before any LLM request is made.

The analysis includes:

- Python AST analysis
- Security rules
- Bandit
- Regex-based checks
- Duplicate detection
- Architecture analysis
- Testing analysis
- Documentation analysis
- JavaScript/TypeScript checks

### 2. Risk-Based AI Review

The AI does not review the entire repository blindly.

The system:

1. Runs static analysis
2. Identifies the riskiest files
3. Selects a limited number of files
4. Sends relevant code to the LLM
5. Validates the returned issues
6. Adds only valid issues to the final report

This helps reduce unnecessary LLM usage and keeps the review focused.

---

## 🤖 LLM Provider Strategy

The application uses a provider-independent LLM layer.

```text
                AI Request
                    │
                    ▼
                  Groq
                 Primary
                    │
             if unavailable
                    ▼
                 Gemini
                Fallback
                    │
             if unavailable
                    ▼
        Static-analysis-only
```

### Current Providers

| Provider | Role |
|---|---|
| Groq | Primary LLM provider |
| Google Gemini | Fallback LLM provider |

The application can still perform static analysis if no AI provider is configured.

---

## 💬 AI Developer Mentor

The AI Developer Mentor uses RAG-style retrieval over the analyzed codebase.

Instead of answering only from general programming knowledge, it retrieves relevant code chunks and detected issues before generating an answer.

```text
User Question
      │
      ▼
Code / Issue Retrieval
      │
      ▼
Relevant File Chunks
      │
      ▼
Issue Context
      │
      ▼
     LLM
      │
      ▼
Grounded Developer Answer
```

The current retriever uses **BM25 keyword search** with path and token matching.

Future versions can replace this with vector embeddings and `pgvector` for semantic retrieval.

---

## 📊 Deterministic Scoring

The health score is **not generated by the LLM**.

It is calculated using a deterministic scoring formula based on detected issues.

This makes the score:

- Reproducible
- Explainable
- Independent of LLM opinions

The score is intended as automated development guidance and is **not a certification or professional code audit**.

---

## 🔐 Security Design

Security is an important part of the project because users can upload arbitrary source code.

### Uploaded Code Is Never Executed

Uploaded repositories are treated as untrusted data.

The application analyzes source files without executing the uploaded code.

### ZIP Protection

ZIP extraction includes protection against:

- Zip-slip / path traversal
- Absolute paths
- Symlinks
- Oversized archives
- Excessive extracted data
- Excessive file counts
- Oversized individual files

### GitHub Repository Protection

GitHub repositories are:

- Public repositories only
- Shallow cloned
- Cloned with Git hooks disabled
- `.git` directory removed after cloning

### Prompt Injection Protection

Repository content is treated as untrusted data.

The AI is instructed not to follow instructions found inside:

- Source code
- Comments
- README files
- Configuration files
- Other repository content

LLM responses are also parsed and validated before being included in the final analysis.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 18, TypeScript |
| Routing | Angular Router |
| HTTP | Angular HttpClient |
| Backend | Python, FastAPI |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Authentication | JWT |
| Code Analysis | Python AST, Bandit, Custom Analyzers |
| Retrieval | BM25 |
| AI | Groq, Google Gemini |
| AI Architecture | RAG-based Developer Mentor |
| Database | SQLite / PostgreSQL |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |

---

## 📁 Project Structure

```text
ai-code-reviewer/
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── llm.py
│   │   │   ├── prompts.py
│   │   │   └── retriever.py
│   │   │
│   │   ├── analyzers/
│   │   │   ├── architecture_analyzer.py
│   │   │   ├── duplicate_analyzer.py
│   │   │   ├── javascript_analyzer.py
│   │   │   ├── project_analyzer.py
│   │   │   ├── python_analyzer.py
│   │   │   ├── security_analyzer.py
│   │   │   └── testing_analyzer.py
│   │   │
│   │   ├── api/
│   │   │   ├── analysis.py
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── deps.py
│   │   │   ├── issues.py
│   │   │   └── repositories.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   │
│   ├── tests/
│   ├── pytest.ini
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── configure.ts
│   └── package.json
│
├── docs/
│   ├── api.md
│   ├── architecture.md
│   └── database.md
│
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
```

---

# 🚀 Run Locally

## Prerequisites

- Python 3.10+
- Node.js 18+
- Node.js 20/22 recommended
- Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/kumarsaurabh6039/ai-code-reviewer.git
cd ai-code-reviewer
```

---

## 2. Backend Setup

```bash
cd backend
```

### Create Virtual Environment

#### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

#### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Create your environment file.

### Windows

```powershell
copy .env.example .env
```

### macOS / Linux

```bash
cp .env.example .env
```

Example:

```env
DATABASE_URL=sqlite:///./app.db

SECRET_KEY=change-this-to-a-long-random-secret

LLM_PROVIDER=groq

GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b

GEMINI_API_KEY=
GEMINI_MODEL=

CORS_ORIGINS=http://localhost:4200

WORKDIR=./workdir

MAX_ZIP_MB=50
MAX_EXTRACTED_MB=200
MAX_FILES=5000
MAX_FILE_KB=300
MAX_REPO_MB_CLONE=300

LLM_MAX_FILES=8
LLM_MAX_CHARS_PER_FILE=14000
```

> Never commit `.env` files or API keys to GitHub.

---

## 4. Start the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload --port 8000
```

Open the API documentation:

http://localhost:8000/docs

Health check:

http://localhost:8000/health

---

# 🎨 Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
```

Start Angular:

```bash
npx ng serve
```

Open:

http://localhost:4200

---

## Frontend API Configuration

The frontend API URL is configured in:

```text
frontend/configure.ts
```

### Local Development

```typescript
export const API_URL = 'http://localhost:8000/api';
```

### Production

```typescript
export const API_URL =
  'https://ai-code-reviewer-t92y.onrender.com/api';
```

---

# 🧪 Run Tests

From the backend directory:

```bash
cd backend
pytest -q
```


# 🗄️ PostgreSQL

SQLite is sufficient for local development.

PostgreSQL can be used for production by setting:


DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE


The application uses SQLAlchemy, so the database backend can be changed through configuration without changing the core application architecture.



# ☁️ Deployment

## Backend — Render

### Build Command


pip install -r requirements.txt


### Start Command


uvicorn app.main:app --host 0.0.0.0 --port $PORT


### Production Backend

https://ai-code-reviewer-t92y.onrender.com

### Required Environment Variables


DATABASE_URL=...
SECRET_KEY=...

LLM_PROVIDER=groq

GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b

GEMINI_API_KEY=...
GEMINI_MODEL=...

CORS_ORIGINS=https://ai-code-reviewer-aarzu.vercel.app


## Frontend — Vercel

Build the Angular application:


npm run build


The current deployable browser output is:


dist/frontend/browser

Production API URL:


https://ai-code-reviewer-t92y.onrender.com/api


### Production Frontend

https://ai-code-reviewer-aarzu.vercel.app



# ⚙️ Configuration Reference

| Variable | Purpose |
| `DATABASE_URL` | SQLite/PostgreSQL connection |
| `SECRET_KEY` | JWT signing secret |
| `LLM_PROVIDER` | Primary LLM provider (`groq` or `gemini`) |
| `GROQ_API_KEY` | Groq API key |
| `GROQ_MODEL` | Groq model |
| `GEMINI_API_KEY` | Gemini API key |
| `GEMINI_MODEL` | Gemini model |
| `CORS_ORIGINS` | Allowed frontend origins |
| `WORKDIR` | Temporary project workspace |
| `MAX_ZIP_MB` | Maximum ZIP upload size |
| `MAX_EXTRACTED_MB` | Maximum extracted data |
| `MAX_FILES` | Maximum number of files |
| `MAX_FILE_KB` | Maximum individual file size |
| `MAX_REPO_MB_CLONE` | Maximum GitHub clone size |
| `LLM_MAX_FILES` | Maximum risky files sent to AI |
| `LLM_MAX_CHARS_PER_FILE` | Maximum characters per file sent to AI |



# ⚠️ Known Limitations

- Analysis currently runs through FastAPI background tasks rather than Celery/Redis workers.
- A running analysis can be lost if the server restarts.
- BM25 is currently used for code retrieval instead of vector embeddings.
- Uploaded files are stored on server disk in `workdir/`.
- Object storage is recommended for production deployments.
- JWT tokens are currently stored in `localStorage`.
- Rate limiting has not yet been implemented.
- Only public GitHub repositories are supported.
- Python has deeper AST-based analysis.
- JavaScript/TypeScript currently use lighter analysis rules.
- AI review quality depends on the configured LLM provider and available API quota.



# 🔮 Roadmap

- [ ] PDF report export
- [ ] Private GitHub repositories via OAuth
- [ ] Branch selection
- [ ] Review history
- [ ] Issue tracking across re-analyses
- [ ] Java analyzer
- [ ] Kotlin analyzer
- [ ] Dart/Flutter analyzer
- [ ] Vector embeddings
- [ ] pgvector semantic retrieval
- [ ] Background workers with Redis/Celery
- [ ] Object storage for uploaded repositories
- [ ] Rate limiting
- [ ] Advanced security scanning
- [ ] CI/CD integration
- [ ] Pull Request review automation


# 🎯 Why I Built This

Most code review tools focus on individual files or pull requests.

This project explores a different workflow:


Analyze the entire codebase
            ↓
Identify the highest-risk problems
            ↓
Explain the problems
            ↓
Create an improvement roadmap
            ↓
Ask questions about the actual codebase


The goal is to combine deterministic software analysis with LLM-powered developer assistance while keeping AI responses grounded in the actual source code.



# 📄 License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for details.



# 👨‍💻 Author

**Saurabh Kumar Singh**

- GitHub: https://github.com/kumarsaurabh6039
- LinkedIn: https://www.linkedin.com/in/saurabh-kumar-singh-7391aa2b/



⭐ If you find this project useful, consider giving the repository a star.