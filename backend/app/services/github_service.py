import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from github import Github
from github.GithubException import GithubException

from ..config import settings
from ..db.database import get_supabase
from ..models.github_repository import (
    GitHubRepository,
    GitHubRepositoryCreate,
    CIFailure,
    CIFailureCreate,
    RepositoryContext,
    GitHubWebhookPayload,
)
from ..models.ticket import TicketCreate, TicketStatus, TicketPriority


logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self):
        self.github_token = getattr(settings, "github_token", None)
        self.github_client = (
            Github(self.github_token)
            if self.github_token and self.github_token != "your_github_token_here"
            else None
        )
        self.org_name = getattr(settings, "github_org_name", "tickarus-demo-org")
        self.webhook_secret = getattr(settings, "github_webhook_secret", None)
        self._ticket_service = None

    @property
    def ticket_service(self):
        """Lazy import to avoid circular dependencies"""
        if self._ticket_service is None:
            from .ticket_service import TicketService

            self._ticket_service = TicketService()
        return self._ticket_service

    async def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature"""
        # Skip verification in dev mode if no webhook secret is set
        return True
        if not self.webhook_secret:
            logger.warning(
                "No webhook secret configured, skipping signature verification"
            )
            return True  # Skip verification in dev mode

        if not signature:
            logger.warning(
                "No signature provided in webhook request - allowing in dev mode"
            )
            return True  # Allow in dev mode when signature is missing

        try:
            # GitHub sends signature as "sha256=<hex_digest>"
            expected_signature = hmac.new(
                self.webhook_secret.encode("utf-8"), payload, hashlib.sha256
            ).hexdigest()

            expected_sig_string = f"sha256={expected_signature}"

            logger.info(f"Expected signature: {expected_sig_string}")
            logger.info(f"Received signature: {signature}")

            # Compare the signatures
            is_valid = hmac.compare_digest(expected_sig_string, signature)

            if not is_valid:
                logger.error("Webhook signature verification failed")
            else:
                logger.info("Webhook signature verified successfully")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    async def create_repository(
        self, repo_data: GitHubRepositoryCreate
    ) -> GitHubRepository:
        """Create a new GitHub repository record"""
        supabase = get_supabase()

        full_name = f"{repo_data.org_name}/{repo_data.repo_name}"

        # Check if repository already exists
        existing = (
            supabase.table("github_repositories")
            .select("*")
            .eq("full_name", full_name)
            .execute()
        )
        if existing.data:
            raise ValueError(f"Repository {full_name} already exists")

        repo_record = {
            "org_name": repo_data.org_name,
            "repo_name": repo_data.repo_name,
            "full_name": full_name,
            "description": repo_data.description,
            "primary_language": repo_data.primary_language,
            "team_id": str(repo_data.team_id) if repo_data.team_id else None,
            "created_at": datetime.utcnow().isoformat(),
        }

        result = supabase.table("github_repositories").insert(repo_record).execute()
        return GitHubRepository(**result.data[0])

    async def get_repository_by_full_name(
        self, full_name: str
    ) -> Optional[GitHubRepository]:
        """Get repository by full name (org/repo)"""
        from ..db.database import get_service_client

        supabase = get_service_client()  # Use service role for system operations

        result = (
            supabase.table("github_repositories")
            .select("*")
            .eq("full_name", full_name)
            .execute()
        )
        if result.data:
            return GitHubRepository(**result.data[0])
        return None

    async def get_repository_context(self, full_name: str) -> Dict:
        """Gather comprehensive repository context for AI analysis"""
        if not self.github_client:
            logger.warning("GitHub client not configured")
            return {}

        try:
            repo = self.github_client.get_repo(full_name)

            # Get recent commits (last 10)
            commits = []
            for commit in repo.get_commits()[:10]:
                commits.append(
                    {
                        "sha": commit.sha,
                        "message": commit.commit.message,
                        "author": (
                            commit.commit.author.name
                            if commit.commit.author
                            else "Unknown"
                        ),
                        "date": (
                            commit.commit.author.date.isoformat()
                            if commit.commit.author
                            else None
                        ),
                        "files_changed": (
                            [f.filename for f in commit.files] if commit.files else []
                        ),
                    }
                )

            # Get open PRs
            open_prs = []
            for pr in repo.get_pulls(state="open"):
                open_prs.append(
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "user": pr.user.login if pr.user else "Unknown",
                        "created_at": pr.created_at.isoformat(),
                        "labels": [label.name for label in pr.labels],
                    }
                )

            # Get recent issues
            recent_issues = []
            for issue in repo.get_issues(state="all")[:20]:
                if not issue.pull_request:  # Exclude PRs
                    recent_issues.append(
                        {
                            "number": issue.number,
                            "title": issue.title,
                            "state": issue.state,
                            "labels": [label.name for label in issue.labels],
                            "created_at": issue.created_at.isoformat(),
                            "body": (
                                issue.body[:500] if issue.body else ""
                            ),  # Truncate for context
                        }
                    )

            # Get repository languages
            languages = repo.get_languages()

            # Get key files structure
            key_files = await self._get_key_files_structure(repo)

            context = {
                "repository": {
                    "name": repo.full_name,
                    "description": repo.description,
                    "language": repo.language,
                    "languages": languages,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                },
                "recent_commits": commits,
                "open_prs": open_prs,
                "recent_issues": recent_issues,
                "file_structure": key_files,
                "last_updated": datetime.utcnow().isoformat(),
            }

            # Cache this context
            await self._cache_repository_context(full_name, context)

            return context

        except GithubException as e:
            logger.error(f"GitHub API error for {full_name}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting context for {full_name}: {e}")
            return {}

    async def _get_key_files_structure(self, repo) -> List[Dict]:
        """Get important files from repository"""
        key_files = []
        important_files = [
            "README.md",
            "package.json",
            "requirements.txt",
            "Dockerfile",
            "docker-compose.yml",
            ".github/workflows",
            "src/",
            "app/",
            "lib/",
        ]

        try:
            contents = repo.get_contents("")
            for content in contents:
                if any(important in content.path for important in important_files):
                    key_files.append(
                        {
                            "path": content.path,
                            "type": content.type,
                            "size": content.size if hasattr(content, "size") else 0,
                        }
                    )
        except Exception as e:
            logger.warning(f"Could not get file structure: {e}")

        return key_files

    async def _cache_repository_context(self, full_name: str, context: Dict):
        """Cache repository context in database"""
        supabase = get_supabase()

        # Get repository ID
        repo_result = (
            supabase.table("github_repositories")
            .select("id")
            .eq("full_name", full_name)
            .execute()
        )
        if not repo_result.data:
            return

        repo_id = repo_result.data[0]["id"]

        # Update or insert context
        context_record = {
            "repo_id": repo_id,
            "context_type": "full_context",
            "context_data": context,
            "last_updated": datetime.utcnow().isoformat(),
        }

        existing = (
            supabase.table("repository_context")
            .select("id")
            .eq("repo_id", repo_id)
            .eq("context_type", "full_context")
            .execute()
        )

        if existing.data:
            supabase.table("repository_context").update(context_record).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            supabase.table("repository_context").insert(context_record).execute()

    async def handle_ci_failure_webhook(
        self, payload: GitHubWebhookPayload
    ) -> Optional[UUID]:
        """Handle CI failure webhook and create ticket"""
        if payload.action not in ["completed"] or not payload.workflow_run:
            return None

        workflow_run = payload.workflow_run
        if workflow_run.get("conclusion") != "failure":
            return None

        full_name = payload.repository["full_name"]
        repo = await self.get_repository_by_full_name(full_name)

        if not repo or not repo.id:
            logger.warning(f"Repository {full_name} not found in database")
            return None

        # Create CI failure record
        ci_failure_data = CIFailureCreate(
            repo_id=repo.id,
            workflow_name=workflow_run.get("name", "Unknown"),
            commit_sha=workflow_run.get("head_sha", ""),
            branch_name=workflow_run.get("head_branch", "main"),
            failure_reason=f"Workflow '{workflow_run.get('name')}' failed",
            logs=await self._get_workflow_logs(full_name, workflow_run.get("id") or 0),
        )

        from ..db.database import get_service_client

        supabase = get_service_client()  # Use service role for system operations
        ci_failure_record = {
            "repo_id": str(ci_failure_data.repo_id),
            "workflow_name": ci_failure_data.workflow_name,
            "commit_sha": ci_failure_data.commit_sha,
            "branch_name": ci_failure_data.branch_name,
            "failure_reason": ci_failure_data.failure_reason,
            "logs": ci_failure_data.logs,
            "created_at": datetime.utcnow().isoformat(),
        }

        ci_result = supabase.table("ci_failures").insert(ci_failure_record).execute()
        ci_failure_id = ci_result.data[0]["id"]

        # Create automated ticket
        repo_context = await self.get_repository_context(full_name)
        ticket_description = self._format_ci_failure_description(
            ci_failure_data, repo_context, payload
        )

        # Ensure we have a valid team_id - if repo has no team, skip ticket creation
        if not repo.team_id:
            logger.warning(
                f"Repository {full_name} has no team_id, cannot create ticket"
            )
            return None

        ticket_data = TicketCreate(
            team_id=repo.team_id,
            title=f"CI Failure: {ci_failure_data.workflow_name} in {repo.repo_name}",
            description=ticket_description,
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
        )

        # Create ticket through ticket service using service client and CI bot
        CI_BOT_UUID = "00000000-0000-4000-8000-000000000001"  # CI Automation Bot
        # Get CI bot actor ID
        from ..services.actor_service import ActorService

        ci_bot_actor = await ActorService.get_actor_for_system_user(UUID(CI_BOT_UUID), client=supabase)

        if not ci_bot_actor:
            logger.error("CI Bot actor not found")
            return None

        ticket = await self.ticket_service.create_ticket(
            ticket_data, ci_bot_actor.id, client=supabase
        )

        # Link CI failure to ticket
        supabase.table("ci_failures").update({"ticket_id": str(ticket.id)}).eq(
            "id", ci_failure_id
        ).execute()

        # Auto-tag the ticket
        await self.ticket_service.add_tags(
            ticket.id,
            [
                "ci-failure",
                "automated",
                repo.repo_name,
                repo.primary_language or "unknown",
            ],
            client=supabase,
        )

        logger.info(f"Created ticket {ticket.id} for CI failure in {full_name}")
        return ticket.id

    def _format_ci_failure_description(
        self,
        ci_failure: CIFailureCreate,
        repo_context: Dict,
        payload: GitHubWebhookPayload,
    ) -> str:
        """Format CI failure into ticket description"""
        workflow_run = payload.workflow_run

        description = f"""## CI/CD Failure Report

**Repository:** {payload.repository['full_name']}
**Workflow:** {ci_failure.workflow_name}
**Branch:** {ci_failure.branch_name}
**Commit:** {ci_failure.commit_sha[:8]}
**Failure Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

### Failure Details
{ci_failure.failure_reason}

### Recent Context
"""

        if repo_context.get("recent_commits"):
            description += "\n**Recent Commits:**\n"
            for commit in repo_context["recent_commits"][:3]:
                description += f"- `{commit['sha'][:8]}` {commit['message'][:100]}...\n"

        if ci_failure.logs:
            description += f"\n### Build Logs\n```\n{ci_failure.logs}\n```\n"

        if workflow_run and isinstance(workflow_run, dict):
            description += (
                f"\n**GitHub Workflow:** {workflow_run.get('html_url', 'N/A')}"
            )
        else:
            description += f"\n**GitHub Workflow:** N/A"

        return description

    async def _get_workflow_logs(self, full_name: str, run_id: int) -> Optional[str]:
        """Get workflow logs from GitHub API"""
        if not self.github_token:
            return None

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                headers = {
                    "Authorization": f"token {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }

                # Get workflow jobs
                response = await client.get(
                    f"https://api.github.com/repos/{full_name}/actions/runs/{run_id}/jobs",
                    headers=headers,
                )

                if response.status_code == 200:
                    jobs = response.json().get("jobs", [])
                    logs = []

                    for job in jobs:
                        if job.get("conclusion") == "failure":
                            logs.append(f"Job: {job.get('name', 'Unknown')}")
                            logs.append(f"Conclusion: {job.get('conclusion')}")

                            # Get detailed logs for this job
                            job_id = job.get("id")
                            if job_id:
                                try:
                                    log_response = await client.get(
                                        f"https://api.github.com/repos/{full_name}/actions/jobs/{job_id}/logs",
                                        headers=headers,
                                    )
                                    if log_response.status_code == 200:
                                        job_logs = log_response.text

                                        if job_logs.strip():
                                            # Extract relevant error lines (last 50 lines or error-containing lines)
                                            log_lines = job_logs.split("\n")
                                            error_lines = [
                                                line
                                                for line in log_lines
                                                if any(
                                                    keyword in line.lower()
                                                    for keyword in [
                                                        "error",
                                                        "fail",
                                                        "exception",
                                                        "stderr",
                                                        "exit code",
                                                        "npm err",
                                                        "fatal",
                                                    ]
                                                )
                                            ]

                                            if error_lines:
                                                logs.append("Error details:")
                                                logs.extend(error_lines)
                                            else:
                                                # If no specific errors, get last 40 lines of meaningful content
                                                logs.append("Last output:")
                                                relevant_lines = [
                                                    line
                                                    for line in log_lines[-40:]
                                                    if line.strip()
                                                ]
                                                logs.extend(relevant_lines)
                                        else:
                                            logs.append("Logs were empty")

                                        # Also add job steps information
                                        steps = job.get("steps", [])
                                        failed_steps = [
                                            step
                                            for step in steps
                                            if step.get("conclusion") == "failure"
                                        ]
                                        if failed_steps:
                                            logs.append("Failed steps:")
                                            for step in failed_steps:
                                                logs.append(
                                                    f"- {step.get('name')}: {step.get('conclusion')}"
                                                )

                                    elif log_response.status_code == 404:
                                        logs.append(
                                            "Logs not available (may have expired)"
                                        )
                                    else:
                                        logs.append(
                                            f"Could not fetch logs (HTTP {log_response.status_code})"
                                        )

                                except Exception as log_error:
                                    logs.append(
                                        f"Could not fetch detailed logs: {log_error}"
                                    )

                            # Add additional job context
                            logs.append(f"Job URL: {job.get('html_url', 'N/A')}")
                            logs.append(f"Started at: {job.get('started_at', 'N/A')}")
                            logs.append(
                                f"Completed at: {job.get('completed_at', 'N/A')}"
                            )

                            logs.append("---")

                    return "\n".join(logs)

        except Exception as e:
            logger.warning(f"Could not fetch workflow logs: {e}")

        return "Logs unavailable"

    async def list_repositories(
        self, team_id: Optional[UUID] = None
    ) -> List[GitHubRepository]:
        """List GitHub repositories, optionally filtered by team"""
        supabase = get_supabase()

        query = supabase.table("github_repositories").select("*").eq("is_active", True)
        if team_id:
            query = query.eq("team_id", str(team_id))

        result = query.execute()
        return [GitHubRepository(**repo) for repo in result.data]
