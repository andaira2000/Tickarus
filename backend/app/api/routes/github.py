import json
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from supabase import AsyncClient

from app.api.dependencies import (
    get_supabase_request_client,
    get_supabase_service_client,
)
from app.models.github_repository import (
    GitHubRepository,
    GitHubRepositoryCreate,
    GitHubRepositoryUpdate,
    GitHubWebhookPayload,
    CIFailure,
    RepositoryContext,
)
from app.services.github_service import github_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/github", tags=["GitHub Integration"])


@router.post("/repositories", response_model=GitHubRepository)
async def create_repository(
    repo_data: GitHubRepositoryCreate,
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Create a new GitHub repository record."""
    try:
        return await github_service.create_repository(repo_data, supabase_client)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/repositories", response_model=List[GitHubRepository])
async def list_repositories(
    team_id: Optional[UUID] = None,
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """List GitHub repositories, optionally filtered by team."""
    return await github_service.list_repositories(team_id, supabase_client)


@router.get("/repositories/{full_name:path}/context")
async def get_repository_context(
    full_name: str,
    supabase_client: AsyncClient = Depends(get_supabase_service_client),
):
    """Get comprehensive repository context for AI analysis."""
    context = await github_service.get_repository_context(full_name)
    if not context:
        raise HTTPException(status_code=404, detail="Repository context not available")
    return context


@router.get("/repositories/{full_name:path}", response_model=GitHubRepository)
async def get_repository(
    full_name: str,
):
    """Get repository by full name (org/repo)"""
    try:
        repo = await github_service.get_repository_by_full_name(full_name)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        return repo
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repository {full_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhooks/ci-failure")
async def handle_ci_failure_webhook(
    request: Request,
    supabase_client: AsyncClient = Depends(get_supabase_service_client),
):
    """Handle GitHub webhook for CI/CD failures."""
    payload = await request.body()

    payload_data = json.loads(payload.decode("utf-8"))
    webhook_payload = GitHubWebhookPayload(**payload_data)

    # Handle ping events
    if webhook_payload.zen:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Webhook ping received",
                "zen": webhook_payload.zen,
            },
        )

    # Handle the workflow webhook
    ticket_id = await github_service.handle_ci_failure_webhook(
        webhook_payload, supabase_client
    )

    if ticket_id:
        return JSONResponse(
            status_code=200,
            content={
                "message": "CI failure processed",
                "ticket_id": str(ticket_id),
            },
        )
    else:
        return JSONResponse(
            status_code=200,
            content={"message": "Webhook received but no action taken"},
        )


@router.get(
    "/repositories/{full_name:path}/ci-failures", response_model=List[CIFailure]
)
async def get_repository_ci_failures(
    full_name: str,
    limit: int = 20,
):
    """Get CI failures for a repository"""
    try:
        repo = await github_service.get_repository_by_full_name(full_name)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Get CI failures from database
        from ...db.database import get_supabase

        supabase = get_supabase()

        result = (
            supabase.table("ci_failures")
            .select("*")
            .eq("repo_id", str(repo.id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return [CIFailure(**failure) for failure in result.data]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CI failures for {full_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def github_health_check():
    """Check health of GitHub integration"""
    try:
        user = github_service.github_client.get_user()
        return {
            "status": "healthy",
            "github_api": "connected",
            "authenticated_user": user.login,
            "organization": github_service.org_name,
        }
    except Exception as e:
        logger.error(f"GitHub health check failed: {e}")
        return {"status": "unhealthy", "github_api": "error", "error": str(e)}
