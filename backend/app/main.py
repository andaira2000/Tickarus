from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.db.database import init_supabase
from app.api.routes import auth, tickets, comments, tags, teams, github

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize base Supabase client once
    init_supabase()
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
