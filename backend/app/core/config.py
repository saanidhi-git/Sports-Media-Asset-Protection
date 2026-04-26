import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Any
from pydantic import field_validator
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Force load the .env file
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(base_dir, ".env"))

class Settings(BaseSettings):
    PROJECT_NAME: str = "SHIELD_MEDIA"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # 60 minutes * 24 hours * 8 days = 11520 minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # CORS
    BACKEND_CORS_ORIGINS: Any = ["http://localhost:4200"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str) and v.startswith("["):
            import json
            return json.loads(v)
        return ["http://localhost:4200"]

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "shield_media"
    DATABASE_URL: Optional[str] = None
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # External API Keys — server will refuse to start if these are blank
    YOUTUBE_API_KEY: str
    TAVILY_API_KEY: str
    OPENROUTER_API_KEY: str
    EXTERNAL_AGENT_KEY: str = "dev-key-123"
    
    # Cloudinary
    CLOUDINARY_URL: Optional[str] = None

    # SMTP Settings
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = "SHIELD_MEDIA"

    @field_validator("EMAILS_FROM_EMAIL", mode="before")
    @classmethod
    def set_default_from_email(cls, v: Optional[str], info: Any) -> Any:
        if v:
            return v
        return info.data.get('SMTP_USER')

    # Streaming Configuration
    STREAM_MODE: bool = True
    EARLY_EXIT_THRESHOLD: float = 0.85
    AUDIO_SEGMENT_DURATION: int = 30  # Reduced from 60 to save RAM
    STREAM_OPEN_TIMEOUT_MS: int = 15_000
    STREAM_READ_TIMEOUT_MS: int = 10_000

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str) and v:
            return v
        
        # Check environment variables directly
        db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
        
        if db_url:
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            print(f"📡 DATABASE: Using Supabase/Cloud URL")
            return db_url
            
        print("⚠️ DATABASE: No DATABASE_URL found, falling back to localhost")
        user = info.data.get('POSTGRES_USER')
        password = quote_plus(str(info.data.get('POSTGRES_PASSWORD', '')))
        server = info.data.get('POSTGRES_SERVER')
        db = info.data.get('POSTGRES_DB')
        
        return f"postgresql://{user}:{password}@{server}/{db}"

    model_config = SettingsConfigDict(
        case_sensitive=True, 
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        extra="ignore"
    )

settings = Settings()
