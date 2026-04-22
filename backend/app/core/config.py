from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Any
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "SHIELD_MEDIA"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "shield_media"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str):
            return v
        return f"postgresql://{info.data.get('POSTGRES_USER')}:{info.data.get('POSTGRES_PASSWORD')}@{info.data.get('POSTGRES_SERVER')}/{info.data.get('POSTGRES_DB')}"

    model_config = SettingsConfigDict(
        case_sensitive=True, 
        env_file="D:/Projects/Sports-Media-Asset-Protection/backend/.env",
        extra="ignore"
    )

settings = Settings()
