from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.db.database import init_supabase
from app.api.routes import auth, tickets, comments, tags, teams, github, metrics, ai_chat
from app.api import evaluation
from app.services.llm_interface import (
    initialize_llm_service, OpenAIProvider, AnthropicProvider, MockLLMProvider
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize base Supabase client once
    init_supabase()

    # Initialize LLM service based on configuration
    try:
        if settings.llm_provider == "openai" and settings.openai_api_key:
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_model
            )
            logger.info(f"Initialized OpenAI provider with model {settings.openai_model}")
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            provider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model
            )
            logger.info(f"Initialized Anthropic provider with model {settings.anthropic_model}")
        else:
            provider = MockLLMProvider()
            logger.info("Initialized Mock LLM provider (no API costs)")

        initialize_llm_service(provider)
    except Exception as e:
        logger.warning(f"Failed to initialize LLM provider: {e}. Using mock provider.")
        initialize_llm_service(MockLLMProvider())

    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS (adjust for your frontend origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "backend"}


# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["tickets"])
app.include_router(comments.router, prefix="/api/comments", tags=["comments"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(github.router, prefix="/api", tags=["github"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(ai_chat.router, prefix="/api/ai-chat", tags=["ai-chat"])
app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])
