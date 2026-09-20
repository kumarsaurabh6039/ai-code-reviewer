import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import analysis, auth, chat, issues, repositories
from .core.config import settings
from .core.database import Base, engine
from .ai.llm import get_llm

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Code Reviewer & Developer Mentor", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MVP: create tables on startup. For production use Alembic migrations.
Base.metadata.create_all(bind=engine)

api = APIRouter(prefix="/api")
for r in (auth.router, repositories.router, analysis.router, issues.router, chat.router):
    api.include_router(r)
app.include_router(api)


@app.get("/health")
def health():
    return {"status": "ok", "ai_enabled": get_llm().available}
