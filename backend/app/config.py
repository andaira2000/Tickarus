from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Tickarus"
    app_version: str = "0.1.0"

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    github_token: str = ""
    github_org_name: str = "tickarus-demo-org"
    github_webhook_secret: str = ""

    llm_provider: str = "anthropic"
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
