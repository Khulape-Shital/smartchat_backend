from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
from typing import Literal, Optional

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")
 
    DATABASE_URL: str

    
    
    SECRET_KEY: str

 
    ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"

    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GEMINI_API_KEY: str
 
    GOOGLE_CLIENT_ID: Optional[str] = None

    # Email configuration for password reset
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    PASSWORD_RESET_EXPIRE_MINUTES: int = 10
    
    # Frontend URL for password reset links and CORS
    FRONTEND_URL: str = "http://localhost:3000"
    
    # CORS configuration
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3001"]
    CORS_ALLOW_CREDENTIALS: bool = True

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v

settings = Settings()
