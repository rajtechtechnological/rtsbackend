from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database Configuration
    USE_LOCAL_DB: bool = True
    LOCAL_DB_URL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Auth Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Storage Configuration
    USE_LOCAL_STORAGE: bool = True
    LOCAL_UPLOAD_DIR: str = "./uploads"
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Application Configuration
    FRONTEND_URL: str = "http://localhost:3000"

    # AI Configuration
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
