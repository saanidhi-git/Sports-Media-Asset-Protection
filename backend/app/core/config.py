from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Any
from pydantic import field_validator
from urllib.parse import quote_plus

class Settings(BaseSettings):
    PROJECT_NAME: str = "SHIELD_MEDIA"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # 60 minutes * 24 hours * 8 days = 11520 minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "shield_media"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # External API Keys — server will refuse to start if these are blank
    YOUTUBE_API_KEY: str
    TAVILY_API_KEY: str

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str):
            return v
        
        user = info.data.get('POSTGRES_USER')
        password = quote_plus(str(info.data.get('POSTGRES_PASSWORD')))
        server = info.data.get('POSTGRES_SERVER')
        db = info.data.get('POSTGRES_DB')
        
        return f"postgresql://{user}:{password}@{server}/{db}"

    model_config = SettingsConfigDict(
        case_sensitive=True, 
        env_file="D:/Projects/Sports-Media-Asset-Protection/backend/.env",
        extra="ignore"
    )

settings = Settings()
