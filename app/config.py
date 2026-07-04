from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Database ---
    # Prod (docs/01 §2): set DATABASE_URL to the Supabase *transaction-mode
    # pooler* connection string (Supavisor, port 6543), e.g.
    #   postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:6543/postgres
    # When DATABASE_URL is empty, the app falls back to LOCAL_DB_URL (dev).
    DATABASE_URL: str = ""
    LOCAL_DB_URL: str = ""
    # SERVERLESS=true on Vercel: NullPool + no pre-ping (see app/database.py).
    SERVERLESS: bool = False

    # "development" | "production". In production the interactive API docs
    # (/docs, /redoc, /openapi.json) are disabled — set on Vercel.
    ENVIRONMENT: str = "development"

    # Auth Configuration
    # SECURITY (F-11): no default — the app must refuse to start if this is unset.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    # docs/01 §5: short access token + long rotated refresh token
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    # Refresh cookie is Secure by default; set false ONLY for local http dev
    # (browsers drop Secure cookies over plain http on non-localhost hosts).
    REFRESH_COOKIE_SECURE: bool = True

    # --- Storage (docs/01 §2, docs/06 §3) ---
    # Local disk is the dev default; prod uses Supabase Storage via plain REST
    # (no supabase SDK). SUPABASE_URL is the project API URL
    # (https://<ref>.supabase.co), NOT the database URL.
    USE_LOCAL_STORAGE: bool = True
    LOCAL_UPLOAD_DIR: str = "./uploads"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "rts-uploads"

    # Application Configuration
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # tolerate legacy keys (e.g. GEMINI_API_KEY) in .env


settings = Settings()
