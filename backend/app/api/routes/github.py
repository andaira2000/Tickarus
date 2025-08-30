import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ...api.dependencies import get_current_user
from ...models.github_repository import (
    GitHubRepository,
    GitHubRepositoryCreate,
    GitHubRepositoryUpdate,
    GitHubWebhookPayload,
    CIFailure,
    RepositoryContext
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/github", tags=["GitHub Integration"])

# Create a dependency that returns GitHubService instance
def get_github_service():
    from ...services.github_service import GitHubService
    return GitHubService()


@router.post("/repositories", response_model=GitHubRepository)
async def create_repository(
    repo_data: GitHubRepositoryCreate,
    current_user = Depends(get_current_user),
    github_service = Depends(get_github_service)
):
    """Create a new GitHub repository record"""
    try:
        return await github_service.create_repository(repo_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating repository: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/repositories", response_model=List[GitHubRepository])
async def list_repositories(
    team_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    github_service = Depends(get_github_service)
):
    """List GitHub repositories, optionally filtered by team"""
    try:
        return await github_service.list_repositories(team_id=team_id)
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/repositories/{full_name:path}", response_model=GitHubRepository)
async def get_repository(
    full_name: str,
    current_user = Depends(get_current_user),
    github_service = Depends(get_github_service)
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


@router.get("/repositories/{full_name:path}/context")
async def get_repository_context(
    full_name: str,
    current_user = Depends(get_current_user),
    github_service = Depends(get_github_service)
):
    """Get comprehensive repository context for AI analysis"""
    try:
        context = await github_service.get_repository_context(full_name)
        if not context:
            raise HTTPException(status_code=404, detail="Repository context not available")
        return context
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repository context for {full_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhooks/ci-failure")
async def handle_ci_failure_webhook(
    request: Request,
    github_service = Depends(get_github_service)
):
    """Handle GitHub webhook for CI/CD failures"""
    try:
        # Get raw payload for signature verification
        payload = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        # Log headers for debugging
        logger.info(f"Webhook headers: {dict(request.headers)}")
        logger.info(f"Signature header: {signature}")
        
        # Verify webhook signature
        if not await github_service.verify_webhook_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse payload from the raw bytes
        import json
        payload_data = json.loads(payload.decode('utf-8'))
        webhook_payload = GitHubWebhookPayload(**payload_data)
        
        # Handle ping events (GitHub webhook test)
        if webhook_payload.zen is not None:
            return JSONResponse(
                status_code=200,
                content={"message": "Webhook ping received", "zen": webhook_payload.zen}
            )
        
        # Handle the workflow run webhook
        ticket_id = await github_service.handle_ci_failure_webhook(webhook_payload)
        
        if ticket_id:
            return JSONResponse(
                status_code=200,
                content={"message": "CI failure processed", "ticket_id": str(ticket_id)}
            )
        else:
            return JSONResponse(
                status_code=200,
                content={"message": "Webhook received but no action taken"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Error processing webhook")


@router.get("/repositories/{full_name:path}/ci-failures", response_model=List[CIFailure])
async def get_repository_ci_failures(
    full_name: str,
    limit: int = 20,
    current_user = Depends(get_current_user),
    github_service = Depends(get_github_service)
):
    """Get CI failures for a repository"""
    try:
        repo = await github_service.get_repository_by_full_name(full_name)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Get CI failures from database
        from ...db.database import get_supabase
        supabase = get_supabase()
        
        result = (supabase.table("ci_failures")
                 .select("*")
                 .eq("repo_id", str(repo.id))
                 .order("created_at", desc=True)
                 .limit(limit)
                 .execute())
        
        return [CIFailure(**failure) for failure in result.data]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CI failures for {full_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Health check endpoint for GitHub integration
@router.get("/health")
async def github_health_check(github_service = Depends(get_github_service)):
    """Check GitHub integration health"""
    try:
        # Test GitHub API connectivity
        if github_service.github_client:
            try:
                # Simple API test - get the authenticated user
                user = github_service.github_client.get_user()
                return {
                    "status": "healthy",
                    "github_api": "connected",
                    "authenticated_user": user.login,
                    "organization": github_service.org_name
                }
            except Exception as api_error:
                return {
                    "status": "degraded",
                    "github_api": "auth_error",
                    "error": str(api_error)
                }
        else:
            return {
                "status": "degraded",
                "github_api": "not_configured",
                "message": "GitHub token not configured"
            }
    except Exception as e:
        logger.error(f"GitHub health check failed: {e}")
        return {
            "status": "unhealthy",
            "github_api": "error",
            "error": str(e)
        }