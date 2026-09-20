from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    # -------------------------
    # Database
    # -------------------------
    database_url: str = "sqlite:///./app.db"

    # -------------------------
    # Authentication
    # -------------------------
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24

    # -------------------------
    # LLM configuration
    # -------------------------
    llm_provider: str = "groq"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # Gemini fallback
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    # -------------------------
    # Working directory
    # -------------------------
    workdir: str = "./workdir"

    # -------------------------
    # CORS
    # -------------------------
    cors_origins: str = "http://localhost:4200"

    # -------------------------
    # Upload / scan safety limits
    # -------------------------
    max_zip_mb: int = 50
    max_extracted_mb: int = 200
    max_files: int = 5000
    max_file_kb: int = 300
    max_repo_mb_clone: int = 300

    # -------------------------
    # LLM review limits
    # -------------------------
    llm_max_files: int = 8
    llm_max_chars_per_file: int = 14000


settings = Settings()