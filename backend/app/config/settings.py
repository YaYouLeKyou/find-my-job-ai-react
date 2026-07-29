"""
Configuration settings for FindMyJobAI application
Uses Pydantic for validation and environment variables
"""

from pydantic import BaseSettings, AnyHttpUrl
from typing import List, Optional
import os

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:5173,http://localhost:3000"
    SCRAPER_MAX_WORKERS: int = 30
    SCRAPER_TIMEOUT: float = 6.0

    # AI Providers
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    OLLAMA_URL: Optional[AnyHttpUrl] = "http://localhost:11434"
    SERPAPI_KEY: Optional[str] = None

    # France Travail API
    FRANCE_TRAVAIL_CLIENT_ID: Optional[str] = None
    FRANCE_TRAVAIL_CLIENT_SECRET: Optional[str] = None

    # Job Search APIs
    ADZUNA_APP_ID: Optional[str] = None
    ADZUNA_APP_KEY: Optional[str] = None
    JOOBLE_API_KEY: Optional[str] = None
    APIFY_API_KEY: Optional[str] = None

    # Database (future)
    DATABASE_URL: Optional[str] = None

    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    SECRET_KEY: str = "changez-moi-en-production-avec-une-valeur-longue-et-aleatoire"
    JWT_SECRET: str = "changez-moi-en-production-avec-une-valeur-longue-et-aleatoire"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def validate(self):
        """Validate configuration and return service status"""
        services = {
            "groq_configured": bool(self.GROQ_API_KEY),
            "gemini_configured": bool(self.GEMINI_API_KEY),
            "ollama_configured": bool(self.OLLAMA_URL),
            "france_travail_configured": bool(self.FRANCE_TRAVAIL_CLIENT_ID and self.FRANCE_TRAVAIL_CLIENT_SECRET),
            "adzuna_configured": bool(self.ADZUNA_APP_ID and self.ADZUNA_APP_KEY),
            "database_configured": bool(self.DATABASE_URL)
        }
        return services

# Singleton instance
settings = Settings()