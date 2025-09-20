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
import re
from collections import defaultdict


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

        ci_bot_actor = await ActorService.get_actor_for_system_user(
            UUID(CI_BOT_UUID), client=supabase
        )

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

    async def analyze_recent_commits(
        self, full_name: str, failure_time: datetime, max_commits: int = 50
    ) -> Dict:
        """
        Analyze ALL commits in the repository (up to max_commits)
        This provides complete contextual information for root cause analysis
        """
        try:
            if not self.github_client:
                return {"error": "GitHub client not available"}

            repo = self.github_client.get_repo(full_name)

            # Get ALL commits (up to max_commits for performance)
            commits = list(repo.get_commits()[:max_commits])

            commit_analysis = {
                "total_commits": len(commits),
                "commits": [],
                "risk_indicators": [],
                "file_changes": defaultdict(int),
                "authors": defaultdict(int),
                "commit_patterns": self._analyze_commit_patterns(commits),
            }

            for commit in commits[
                :20
            ]:  # Analyze first 20 commits for detailed analysis
                commit_data = await self._analyze_single_commit(repo, commit)
                commit_analysis["commits"].append(commit_data)

                # Track file changes
                for file_info in commit_data.get("files", []):
                    commit_analysis["file_changes"][file_info["filename"]] += 1

                # Track authors
                if commit.author:
                    commit_analysis["authors"][commit.author.login] += 1

                # Identify risk indicators
                risk_indicators = self._identify_commit_risks(commit_data)
                commit_analysis["risk_indicators"].extend(risk_indicators)

            return commit_analysis

        except Exception as e:
            logger.error(f"Error analyzing recent commits: {str(e)}")
            return {"error": str(e)}

    async def _analyze_single_commit(self, repo, commit) -> Dict:
        """Analyze a single commit for potential issues"""
        try:
            commit_data = {
                "sha": commit.sha[:8],
                "message": commit.commit.message,
                "author": commit.author.login if commit.author else "Unknown",
                "date": commit.commit.author.date.isoformat(),
                "files": [],
                "stats": {
                    "additions": commit.stats.additions,
                    "deletions": commit.stats.deletions,
                    "total": commit.stats.total,
                },
            }

            # Analyze changed files
            for file in commit.files:
                file_info = {
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": (
                        file.patch[:1000] if file.patch else None
                    ),  # First 1000 chars
                }

                # Add code analysis for this file
                file_info.update(self._analyze_file_changes(file))
                commit_data["files"].append(file_info)

            return commit_data

        except Exception as e:
            logger.warning(f"Error analyzing commit {commit.sha}: {str(e)}")
            return {"sha": commit.sha[:8], "error": str(e)}

    def _analyze_file_changes(self, file) -> Dict:
        """Analyze code changes in a file for potential issues"""
        analysis = {
            "risk_level": "low",
            "issues": [],
            "language": self._detect_language(file.filename),
            "is_critical_file": self._is_critical_file(file.filename),
        }

        if not file.patch:
            return analysis

        patch_lines = file.patch.split("\n")
        added_lines = [
            line[1:]
            for line in patch_lines
            if line.startswith("+") and not line.startswith("+++")
        ]
        removed_lines = [
            line[1:]
            for line in patch_lines
            if line.startswith("-") and not line.startswith("---")
        ]

        # Analyze added code for potential issues
        for line in added_lines:
            line = line.strip()

            # Check for common problematic patterns
            if self._contains_security_risk(line):
                analysis["issues"].append(f"Security risk: {line[:50]}...")
                analysis["risk_level"] = "high"

            elif self._contains_performance_risk(line):
                analysis["issues"].append(f"Performance risk: {line[:50]}...")
                if analysis["risk_level"] == "low":
                    analysis["risk_level"] = "medium"

            elif self._contains_error_handling_issues(line):
                analysis["issues"].append(f"Error handling issue: {line[:50]}...")
                if analysis["risk_level"] == "low":
                    analysis["risk_level"] = "medium"

        # Large changes are riskier
        if file.changes > 100:
            analysis["issues"].append(f"Large change: {file.changes} lines modified")
            if analysis["risk_level"] == "low":
                analysis["risk_level"] = "medium"

        return analysis

    def _analyze_commit_patterns(self, commits) -> Dict:
        """Analyze patterns across multiple commits"""
        patterns = {
            "commit_frequency": len(commits),
            "message_patterns": [],
            "time_patterns": [],
            "size_patterns": [],
        }

        # Analyze commit messages for patterns
        urgent_keywords = [
            "fix",
            "hotfix",
            "urgent",
            "critical",
            "bug",
            "error",
            "crash",
        ]
        experimental_keywords = ["experiment", "test", "try", "attempt", "wip", "draft"]

        urgent_commits = 0
        experimental_commits = 0

        for commit in commits:
            message = commit.commit.message.lower()

            if any(keyword in message for keyword in urgent_keywords):
                urgent_commits += 1

            if any(keyword in message for keyword in experimental_keywords):
                experimental_commits += 1

        patterns["urgent_commits"] = urgent_commits
        patterns["experimental_commits"] = experimental_commits

        if urgent_commits > len(commits) * 0.3:
            patterns["message_patterns"].append("High frequency of urgent/fix commits")

        if experimental_commits > len(commits) * 0.2:
            patterns["message_patterns"].append(
                "High frequency of experimental commits"
            )

        return patterns

    def _identify_commit_risks(self, commit_data: Dict) -> List[str]:
        """Identify risk indicators in a commit"""
        risks = []

        # Large commits are risky
        if commit_data["stats"]["total"] > 200:
            risks.append(f"Large commit: {commit_data['stats']['total']} lines changed")

        # Check commit message for risk indicators
        message = commit_data["message"].lower()
        risky_phrases = [
            "quick fix",
            "hotfix",
            "urgent",
            "temporary",
            "hack",
            "todo",
            "fixme",
            "workaround",
            "disable",
            "comment out",
        ]

        for phrase in risky_phrases:
            if phrase in message:
                risks.append(f"Risky commit message pattern: '{phrase}'")

        # Check for critical file modifications
        critical_files = 0
        for file_info in commit_data.get("files", []):
            if file_info.get("is_critical_file"):
                critical_files += 1

        if critical_files > 0:
            risks.append(f"Modified {critical_files} critical files")

        return risks

    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename"""
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react-typescript",
            ".java": "java",
            ".go": "go",
            ".cpp": "cpp",
            ".c": "c",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".sql": "sql",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sh": "shell",
            ".dockerfile": "docker",
            ".md": "markdown",
        }

        for ext, lang in extensions.items():
            if filename.lower().endswith(ext):
                return lang

        return "unknown"

    def _is_critical_file(self, filename: str) -> bool:
        """Check if a file is considered critical"""
        critical_patterns = [
            # Config files
            r"\.env",
            r"config\.(py|js|json|yaml|yml)",
            r"settings\.(py|js)",
            # Build/deployment files
            r"Dockerfile",
            r"docker-compose\.ya?ml",
            r"package\.json",
            r"requirements\.txt",
            r"Makefile",
            r"\.github/workflows/",
            r"\.gitlab-ci\.ya?ml",
            # Database files
            r"migrations?/",
            r"schema\.(sql|py|js)",
            r"models\.(py|js)",
            # Authentication/security
            r"auth\.(py|js)",
            r"security\.(py|js)",
            r"middleware\.(py|js)",
            # Main application files
            r"main\.(py|js)",
            r"app\.(py|js)",
            r"server\.(py|js)",
            r"index\.(py|js|html)",
            # Core business logic
            r"core/",
            r"services/",
            r"controllers/",
            r"handlers/",
        ]

        for pattern in critical_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                return True

        return False

    def _contains_security_risk(self, line: str) -> bool:
        """Check if code line contains security risks"""
        security_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',  # Hardcoded passwords
            r'secret\s*=\s*["\'][^"\']+["\']',  # Hardcoded secrets
            r'api_?key\s*=\s*["\'][^"\']+["\']',  # Hardcoded API keys
            r"exec\s*\(",  # Code execution
            r"eval\s*\(",  # Code evaluation
            r"subprocess\.",  # Subprocess calls
            r"shell\s*=\s*True",  # Shell injection risk
            r"\.innerHTML\s*=",  # XSS risk
            r"document\.write\s*\(",  # XSS risk
            r"sql.*\+.*\+",  # SQL injection risk
        ]

        for pattern in security_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True

        return False

    def _contains_performance_risk(self, line: str) -> bool:
        """Check if code line contains performance risks"""
        performance_patterns = [
            r"for.*in.*for.*in",  # Nested loops
            r"while.*while",  # Nested while loops
            r"\.sync\(",  # Synchronous calls
            r"time\.sleep\(",  # Blocking sleep
            r"\.all\(\)\.count\(\)",  # Inefficient database queries
            r"SELECT \* FROM",  # SELECT * queries
            r"setTimeout.*setTimeout",  # Nested timeouts
            r"setInterval",  # Intervals
        ]

        for pattern in performance_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True

        return False

    def _contains_error_handling_issues(self, line: str) -> bool:
        """Check if code line has error handling issues"""
        error_patterns = [
            r"except:?\s*$",  # Bare except
            r"catch\s*\(\s*\)\s*\{",  # Empty catch
            r"pass\s*$",  # Empty pass
            r"// TODO",  # TODO comments
            r"# TODO",  # TODO comments
            r"console\.log\(",  # Debug logging
            r"print\(",  # Debug printing
            r'throw\s+new\s+Error\(\s*["\']["\']',  # Empty error messages
        ]

        for pattern in error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True

        return False

    async def get_commit_context_for_rootcause(
        self,
        full_name: str,
        failure_time: datetime,
        failure_logs: str = "",
        include_full_codebase: bool = True,
    ) -> Dict:
        """
        Get comprehensive commit context for enhanced root cause analysis
        This is the main method called by the root cause service
        """
        try:
            # Analyze ALL commits in repository
            commit_analysis = await self.analyze_recent_commits(full_name, failure_time)

            # Get repository context
            repo_context = await self.get_repository_context(full_name)

            # Correlate failure logs with code changes
            correlation = self._correlate_logs_with_commits(
                failure_logs, commit_analysis.get("commits", [])
            )

            # Get full codebase if requested (for dissertation with small repos)
            full_codebase = None
            if include_full_codebase:
                full_codebase = await self._get_full_repository_code(full_name)

            # Build comprehensive context
            context = {
                "repository": {
                    "name": full_name,
                    "language": repo_context.get("primary_language", "unknown"),
                    "tech_stack": repo_context.get("tech_stack", []),
                },
                "commit_analysis": commit_analysis,
                "log_correlation": correlation,
                "risk_assessment": self._assess_overall_risk(commit_analysis),
                "suggested_focus_areas": self._suggest_focus_areas(
                    commit_analysis, correlation
                ),
                "full_codebase": full_codebase,
            }

            return context

        except Exception as e:
            logger.error(f"Error getting commit context for root cause: {str(e)}")
            return {"error": str(e)}

    def _correlate_logs_with_commits(self, logs: str, commits: List[Dict]) -> Dict:
        """Correlate failure logs with recent commits to find likely causes"""
        correlation = {
            "likely_culprits": [],
            "related_files": [],
            "matching_patterns": [],
        }

        if not logs or not commits:
            return correlation

        log_lines = logs.lower().split("\n")
        error_lines = [
            line
            for line in log_lines
            if any(
                keyword in line for keyword in ["error", "exception", "fail", "crash"]
            )
        ]

        for commit in commits:
            commit_score = 0
            matching_reasons = []

            # Check if commit message relates to error
            commit_message = commit.get("message", "").lower()
            for error_line in error_lines[:5]:  # Check first 5 error lines
                if any(
                    word in commit_message
                    for word in error_line.split()
                    if len(word) > 3
                ):
                    commit_score += 2
                    matching_reasons.append(
                        f"Commit message relates to error: {error_line[:50]}..."
                    )

            # Check if modified files appear in error logs
            for file_info in commit.get("files", []):
                filename = file_info.get("filename", "")
                if filename and filename.lower() in logs.lower():
                    commit_score += 3
                    matching_reasons.append(
                        f"Modified file appears in logs: {filename}"
                    )
                    correlation["related_files"].append(filename)

            # Check for risky patterns
            if file_info.get("risk_level") == "high":
                commit_score += 2
                matching_reasons.append("High-risk code changes detected")

            if commit_score > 0:
                correlation["likely_culprits"].append(
                    {
                        "commit": commit,
                        "confidence_score": min(commit_score * 10, 100),  # Cap at 100%
                        "reasons": matching_reasons,
                    }
                )

        # Sort by confidence score
        correlation["likely_culprits"].sort(
            key=lambda x: x["confidence_score"], reverse=True
        )

        return correlation

    def _assess_overall_risk(self, commit_analysis: Dict) -> Dict:
        """Assess overall risk level based on commit analysis"""
        risk_assessment = {"level": "low", "score": 0, "factors": []}

        # Repository commit activity analysis
        commit_count = commit_analysis.get("total_commits", 0)
        if commit_count > 50:
            risk_assessment["score"] += 2
            risk_assessment["factors"].append(
                f"Very active repository: {commit_count} commits"
            )
        elif commit_count > 20:
            risk_assessment["score"] += 1
            risk_assessment["factors"].append(
                f"Active repository: {commit_count} commits"
            )

        # Risk indicators from individual commits
        risk_indicators = commit_analysis.get("risk_indicators", [])
        risk_assessment["score"] += len(risk_indicators)
        risk_assessment["factors"].extend(risk_indicators)

        # Urgent/experimental commits
        patterns = commit_analysis.get("commit_patterns", {})
        urgent_commits = patterns.get("urgent_commits", 0)
        experimental_commits = patterns.get("experimental_commits", 0)

        if urgent_commits > 2:
            risk_assessment["score"] += urgent_commits
            risk_assessment["factors"].append(
                f"Multiple urgent/fix commits: {urgent_commits}"
            )

        if experimental_commits > 1:
            risk_assessment["score"] += experimental_commits
            risk_assessment["factors"].append(
                f"Experimental commits: {experimental_commits}"
            )

        # Determine risk level
        if risk_assessment["score"] >= 8:
            risk_assessment["level"] = "high"
        elif risk_assessment["score"] >= 4:
            risk_assessment["level"] = "medium"

        return risk_assessment

    def _suggest_focus_areas(
        self, commit_analysis: Dict, correlation: Dict
    ) -> List[str]:
        """Suggest areas to focus on for debugging"""
        suggestions = []

        # Focus on likely culprit commits
        culprits = correlation.get("likely_culprits", [])
        if culprits:
            top_culprit = culprits[0]
            suggestions.append(
                f"Review commit {top_culprit['commit']['sha']} "
                f"(confidence: {top_culprit['confidence_score']}%)"
            )

        # Focus on frequently changed files
        file_changes = commit_analysis.get("file_changes", {})
        if file_changes:
            most_changed = max(file_changes.items(), key=lambda x: x[1])
            if most_changed[1] > 1:
                suggestions.append(
                    f"Focus on {most_changed[0]} (changed {most_changed[1]} times)"
                )

        # Focus on high-risk changes
        risk_indicators = commit_analysis.get("risk_indicators", [])
        high_risk_indicators = [
            r for r in risk_indicators if "high" in r.lower() or "critical" in r.lower()
        ]
        if high_risk_indicators:
            suggestions.append(
                "Review high-risk changes: " + "; ".join(high_risk_indicators[:2])
            )

        # Focus on recent large changes
        commits = commit_analysis.get("commits", [])
        large_commits = [c for c in commits if c.get("stats", {}).get("total", 0) > 100]
        if large_commits:
            suggestions.append(
                f"Review large recent commits: {len(large_commits)} commits with >100 lines changed"
            )

        return suggestions[:5]  # Return top 5 suggestions

    async def _get_full_repository_code(
        self, full_name: str, max_file_size: int = 50000
    ) -> Dict:
        """
        Fetch the complete repository code for LLM analysis
        For dissertation purposes with small test repositories
        """
        try:
            if not self.github_client:
                return {"error": "GitHub client not available"}

            repo = self.github_client.get_repo(full_name)

            # Get default branch
            default_branch = repo.default_branch

            # Get the repository tree
            tree = repo.get_git_tree(default_branch, recursive=True)

            codebase = {
                "repository": full_name,
                "branch": default_branch,
                "files": {},
                "structure": [],
                "total_files": 0,
                "total_size": 0,
            }

            # Filter to code files only
            code_extensions = {
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".java",
                ".go",
                ".cpp",
                ".c",
                ".rs",
                ".rb",
                ".php",
                ".cs",
                ".sql",
                ".yaml",
                ".yml",
                ".json",
                ".xml",
                ".html",
                ".css",
                ".scss",
                ".sh",
                ".dockerfile",
                ".md",
                ".txt",
                ".env",
                ".gitignore",
                ".toml",
                ".ini",
                ".cfg",
                ".conf",
            }

            # Collect file information
            code_files = []
            for element in tree.tree:
                if element.type == "blob":  # It's a file
                    file_path = element.path
                    file_ext = (
                        "." + file_path.split(".")[-1].lower()
                        if "." in file_path
                        else ""
                    )

                    # Include code files and configuration files
                    if file_ext in code_extensions or any(
                        name in file_path.lower()
                        for name in ["makefile", "dockerfile", "readme", "license"]
                    ):

                        code_files.append(
                            {
                                "path": file_path,
                                "sha": element.sha,
                                "size": element.size,
                                "extension": file_ext,
                            }
                        )

            # Sort by importance (critical files first)
            code_files.sort(
                key=lambda f: self._get_file_importance_score(f["path"]), reverse=True
            )

            # Fetch content for files (with size limits for LLM)
            total_content_size = 0
            max_total_size = 200000  # 200KB total limit for LLM context

            for file_info in code_files:
                if total_content_size >= max_total_size:
                    break

                if file_info["size"] > max_file_size:
                    # For large files, just show structure
                    codebase["files"][file_info["path"]] = {
                        "content": f"[File too large: {file_info['size']} bytes]",
                        "size": file_info["size"],
                        "extension": file_info["extension"],
                        "truncated": True,
                    }
                    continue

                try:
                    # Fetch file content
                    file_content = repo.get_contents(file_info["path"])

                    if file_content.content:
                        decoded_content = file_content.decoded_content.decode(
                            "utf-8", errors="ignore"
                        )

                        # Add to total size check
                        if total_content_size + len(decoded_content) > max_total_size:
                            # Truncate if it would exceed limit
                            remaining_space = max_total_size - total_content_size
                            decoded_content = (
                                decoded_content[:remaining_space] + "\n[TRUNCATED]"
                            )

                        codebase["files"][file_info["path"]] = {
                            "content": decoded_content,
                            "size": file_info["size"],
                            "extension": file_info["extension"],
                            "truncated": False,
                        }

                        total_content_size += len(decoded_content)
                        codebase["total_files"] += 1

                except Exception as e:
                    logger.warning(
                        f"Could not fetch content for {file_info['path']}: {e}"
                    )
                    codebase["files"][file_info["path"]] = {
                        "content": f"[Error reading file: {str(e)}]",
                        "size": file_info["size"],
                        "extension": file_info["extension"],
                        "error": str(e),
                    }

            # Create directory structure
            codebase["structure"] = self._build_directory_structure(
                codebase["files"].keys()
            )
            codebase["total_size"] = total_content_size

            logger.info(
                f"Fetched {codebase['total_files']} files ({total_content_size} bytes) from {full_name}"
            )

            return codebase

        except Exception as e:
            logger.error(f"Error fetching full repository code: {str(e)}")
            return {"error": str(e)}

    def _get_file_importance_score(self, file_path: str) -> int:
        """Score files by importance for root cause analysis"""
        score = 0

        # Critical configuration files
        if any(
            name in file_path.lower()
            for name in [
                "package.json",
                "requirements.txt",
                "pom.xml",
                "build.gradle",
                "dockerfile",
                "docker-compose",
                "makefile",
                ".env",
                "config",
            ]
        ):
            score += 100

        # Main application files
        if any(
            name in file_path.lower()
            for name in ["main.", "app.", "server.", "index.", "__init__.py"]
        ):
            score += 80

        # Test files
        if any(name in file_path.lower() for name in ["test", "spec"]):
            score += 60

        # Source code files
        code_extensions = [".py", ".js", ".ts", ".java", ".go", ".cpp", ".c", ".rs"]
        if any(file_path.endswith(ext) for ext in code_extensions):
            score += 40

        # CI/CD files
        if any(
            name in file_path.lower() for name in [".github", ".gitlab", "ci", "cd"]
        ):
            score += 30

        # Documentation
        if any(name in file_path.lower() for name in ["readme", "doc"]):
            score += 20

        return score

    def _build_directory_structure(self, file_paths) -> List[str]:
        """Build a simple directory structure representation"""
        directories = set()

        for path in file_paths:
            parts = path.split("/")
            for i in range(len(parts)):
                dir_path = "/".join(parts[: i + 1])
                directories.add(dir_path)

        return sorted(list(directories))


# Global instance
github_service = GitHubService()
