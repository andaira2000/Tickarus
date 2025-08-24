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

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
