"""
Configuration management for FindMyJobAI Backend
Loads and validates environment variables
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _BACKEND_DIR / ".env"
if _DOTENV_PATH.exists():
    load_dotenv(_DOTENV_PATH, override=True)
else:
    load_dotenv(override=True)


class Settings:
    """Application settings loaded from environment variables."""
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    XAI_API_KEY: str = os.getenv("XAI_API_KEY", "").strip()
    
    # Ollama
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434").strip()
    
    # France Travail
    FRANCE_TRAVAIL_CLIENT_ID: str = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "").strip()
    FRANCE_TRAVAIL_CLIENT_SECRET: str = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "").strip()
    
    # Adzuna
    ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "").strip()
    ADZUNA_APP_KEY: str = os.getenv("ADZUNA_APP_KEY", "").strip()
    
    # SerpApi
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "").strip()
    
    # Jooble
    JOOBLE_API_KEY: str = os.getenv("JOOBLE_API_KEY", "").strip()
    
    # Apify
    APIFY_API_KEY: str = os.getenv("APIFY_API_KEY", "").strip()
    
    # CORS
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://localhost:8501,"
        "https://find-my-job-ai.netlify.app,https://*.netlify.app"
    ).strip()
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost").strip()
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Rate limiting
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "100/minute,10/second")
    
    # Scraping
    SCRAPER_TIMEOUT: int = int(os.getenv("SCRAPER_TIMEOUT", "6"))
    SCRAPER_MAX_WORKERS: int = int(os.getenv("SCRAPER_MAX_WORKERS", "30"))
    
    def validate(self) -> dict:
        """
        Validate configuration and return status of each service.
        
        Returns:
            Dictionary with validation status for each service
        """
        return {
            "groq_key_configured": bool(self.GROQ_API_KEY and self.GROQ_API_KEY.startswith("gsk_")),
            "gemini_key_configured": bool(self.GEMINI_API_KEY),
            "xai_key_configured": bool(self.XAI_API_KEY),
            "ollama_configured": bool(self.OLLAMA_URL),
            "france_travail_configured": bool(self.FRANCE_TRAVAIL_CLIENT_ID and self.FRANCE_TRAVAIL_CLIENT_SECRET),
            "adzuna_configured": bool(self.ADZUNA_APP_ID and self.ADZUNA_APP_KEY),
            "serpapi_configured": bool(self.SERPAPI_KEY),
            "jooble_configured": bool(self.JOOBLE_API_KEY),
            "apify_configured": bool(self.APIFY_API_KEY),
        }
    
    def get_default_model(self) -> str:
        """Get the default AI model based on available API keys."""
        if self.GROQ_API_KEY and self.GROQ_API_KEY.startswith("gsk_"):
            return "Groq / Llama 3.3"
        elif self.GEMINI_API_KEY:
            return "Gemini 3.5"
        elif self.XAI_API_KEY:
            return "Grok"
        else:
            return "Groq / Llama 3.3 (Local/dev)"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings