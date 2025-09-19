from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "Cloud Ticketing System"
    app_version: str = "0.2.0"
    debug_mode: bool = False

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""  # anon key is fine here
    supabase_service_key: Optional[str] = None  # not required by the app
    
    # GitHub Integration
    github_token: Optional[str] = None
    github_org_name: str = "tickarus-demo-org"
    github_webhook_secret: Optional[str] = None

    # LLM Configuration
    llm_provider: str = "mock"  # "openai", "anthropic", or "mock"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-haiku-20240307"
    
    # Auth (legacy fields that may exist in .env)
    secret_key: Optional[str] = None
    algorithm: Optional[str] = None
    access_token_expire_minutes: Optional[str] = None
    backend_cors_origins: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
