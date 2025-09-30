import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from itertools import islice
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from githubkit import GitHub
from githubkit.exception import GitHubException, RequestFailed
from supabase import AsyncClient

from app.config import settings
from app.models.github_repository import (
    GitHubRepository,
    GitHubRepositoryCreate,
    CIFailureCreate,
    GitHubWebhookPayload,
)
from app.models.ticket import TicketCreate, TicketPriority
from app.services.actor_service import ActorService
from app.services.ai_automation_service import AIAutomationService
from app.services.ticket_service import TicketService

logger = logging.getLogger(__name__)

CI_BOT_UUID = "00000000-0000-4000-8000-000000000001"
CI_BOT_ACTOR = None


async def _get_ci_bot_actor(supabase_client: AsyncClient):
    global CI_BOT_ACTOR
    if not CI_BOT_ACTOR:
        CI_BOT_ACTOR = await ActorService.get_actor_for_system_user(
            UUID(CI_BOT_UUID), supabase_client
        )

    return CI_BOT_ACTOR


class GitHubService:
    def __init__(self):
        self.github_token = settings.github_token
        self.github_client = GitHub(auth=self.github_token)
        self.org_name = settings.github_org_name
        self.webhook_secret = settings.github_webhook_secret

    async def create_repository(
        self, repo_data: GitHubRepositoryCreate, supabase_client: AsyncClient
    ) -> GitHubRepository:
        """Create a new GitHub repository record"""
        full_name = f"{repo_data.org_name}/{repo_data.repo_name}"

        existing_repo = (
            await supabase_client.table("github_repositories")
            .select("*")
            .eq("full_name", full_name)
            .execute()
        ).data
        if existing_repo:
            raise ValueError(f"Repository {full_name} already exists")

        repo_record = {
            "org_name": repo_data.org_name,
            "repo_name": repo_data.repo_name,
            "full_name": full_name,
            "description": repo_data.description,
            "primary_language": repo_data.primary_language,
            "team_id": str(repo_data.team_id) if repo_data.team_id else None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = (
            await supabase_client.table("github_repositories")
            .insert(repo_record)
            .execute()
        ).data
        return GitHubRepository(**result[0])

    async def list_repositories(
        self, team_id: Optional[UUID], supabase_client: AsyncClient
    ) -> List[GitHubRepository]:
        """List GitHub repositories, optionally filtered by team."""

        query = (
            supabase_client.table("github_repositories")
            .select("*")
            .eq("is_active", True)
        )
        if team_id:
            query = query.eq("team_id", str(team_id))

        repos = (await query.execute()).data
        return [GitHubRepository(**repo) for repo in repos]

    async def get_repository_by_full_name(
        self, full_name: str, supabase_client: AsyncClient
    ) -> Optional[GitHubRepository]:
        """Get repository by full name (org/repo)."""

        repo = (
            await supabase_client.table("github_repositories")
            .select("*")
            .eq("full_name", full_name)
            .execute()
        ).data
        return GitHubRepository(**repo[0]) if repo else None

    async def handle_ci_failure_webhook(
        self, payload: GitHubWebhookPayload, supabase_client: AsyncClient
    ) -> Optional[UUID]:
        """Handle CI failure webhook and create a ticket."""
        if payload.action not in ["completed"] or not payload.workflow_run:
            return None

        workflow_run = payload.workflow_run
        if workflow_run.get("conclusion") != "failure":
            return None

        full_name = payload.repository["full_name"]
        repo = await self.get_repository_by_full_name(full_name, supabase_client)

        if not repo or not repo.id:
            logger.warning(f"Repository {full_name} not found in database")
            return None

        ci_failure_data = CIFailureCreate(
            repo_id=str(repo.id),
            workflow_name=workflow_run.get("name", "Unknown"),
            commit_sha=workflow_run.get("head_sha", ""),
            branch_name=workflow_run.get("head_branch", "main"),
            failure_reason=f"Workflow '{workflow_run.get('name')}' failed",
            logs=await self._get_workflow_logs(full_name, workflow_run.get("id") or 0),
        )

        ci_failure = (
            await supabase_client.table("ci_failures")
            .insert(ci_failure_data.model_dump())
            .execute()
        ).data
        ci_failure_id = ci_failure[0]["id"]

        # Create automated ticket

        repo_context = await self._get_repository_context(full_name)
        ticket_description = self._format_ci_failure_description(
            ci_failure_data, repo_context, payload
        )

        if not repo.team_id:
            logger.warning(
                f"Repository {full_name} has no team_id, cannot create ticket"
            )
            return None

        ticket_data = TicketCreate(
            team_id=repo.team_id,
            title=f"CI Failure: {ci_failure_data.workflow_name} in {repo.repo_name}",
            description=ticket_description,
            priority=TicketPriority.HIGH,
        )

        ci_bot_actor = await _get_ci_bot_actor(supabase_client)

        ticket = await TicketService.create_ticket(
            ticket_data, ci_bot_actor.id, supabase_client
        )

        # Link CI failure to ticket
        await supabase_client.table("ci_failures").update(
            {"ticket_id": str(ticket.id)}
        ).eq("id", ci_failure_id).execute()

        await TicketService.add_tags(
            ticket.id,
            [
                "ci-failure",
                "automated",
                repo.repo_name,
                repo.primary_language or "unknown",
            ],
            ci_bot_actor.id,
            supabase_client,
        )

        logger.info(f"Created ticket {ticket.id} for CI failure in {full_name}")

        def ai_automation_callback(task: asyncio.Task):
            if task.exception():
                logger.error(
                    f"AI automation failed for ticket {ticket.id}: {str(task.exception())}"
                )
            else:
                logger.info(f"AI automation completed for ticket {ticket.id}")

        asyncio.create_task(
            AIAutomationService.post_ai_root_cause_analysis(ticket.id)
        ).add_done_callback(ai_automation_callback)

        return ticket.id

    async def get_commit_context_for_rootcause(
        self,
        full_name: str,
        failure_time: datetime,
        failure_logs: str = "",
        include_full_codebase: bool = False,
    ) -> Dict:
        """Get detailed commit context for root cause analysis"""
        try:
            commit_analysis = await self._analyze_recent_commits(
                full_name, failure_time
            )

            repo_context = await self._get_repository_context(full_name)

            correlation = self._correlate_logs_with_commits(
                failure_logs, commit_analysis.get("commits", [])
            )

            full_codebase = None
            if include_full_codebase:
                full_codebase = await self._get_full_repository_code(full_name)

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

    def _format_ci_failure_description(
        self,
        ci_failure: CIFailureCreate,
        repo_context: Dict,
        payload: GitHubWebhookPayload,
    ) -> str:
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

    async def _get_key_files_structure(self, owner: str, repo_name: str) -> List[Dict]:
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
            contents_resp = await self.github_client.rest.repos.async_get_content(
                owner=owner, repo=repo_name, path=""
            )
            for content in contents_resp.parsed_data:
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

    async def _get_workflow_logs(self, full_name: str, run_id: int) -> str:
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                headers = {
                    "Authorization": f"token {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                }

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
                                                logs.append("Last output:")
                                                relevant_lines = [
                                                    line
                                                    for line in log_lines[-40:]
                                                    if line.strip()
                                                ]
                                                logs.extend(relevant_lines)
                                        else:
                                            logs.append("Logs were empty")

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

    async def _analyze_recent_commits(
        self, full_name: str, failure_time: datetime, max_commits: int = 50
    ) -> Dict:
        try:
            owner, repo_name = full_name.split("/")
            commits_resp = await self.github_client.rest.repos.async_list_commits(
                owner=owner, repo=repo_name, per_page=max_commits
            )
            commits = commits_resp.parsed_data

            commit_analysis = {
                "total_commits": len(commits),
                "commits": [],
                "risk_indicators": [],
                "file_changes": defaultdict(int),
                "authors": defaultdict(int),
                "commit_patterns": self._analyze_commit_patterns(commits),
            }

            for commit in commits:
                commit_data = await self._analyze_single_commit(
                    owner, repo_name, commit
                )
                commit_analysis["commits"].append(commit_data)

                for file_info in commit_data.get("files", []):
                    commit_analysis["file_changes"][file_info["filename"]] += 1

                if commit.author:
                    commit_analysis["authors"][commit.author.login] += 1

                risk_indicators = self._identify_commit_risks(commit_data)
                commit_analysis["risk_indicators"].extend(risk_indicators)

            logger.info(f"Commit analysis: {commit_analysis}")
            return commit_analysis

        except Exception as e:
            logger.error(f"Error analyzing recent commits: {str(e)}")
            return {"error": str(e)}

    async def _get_repository_context(self, full_name: str) -> Dict:
        try:
            owner, repo_name = full_name.split("/")
            repo_resp = await self.github_client.rest.repos.async_get(
                owner=owner, repo=repo_name
            )
            repo = repo_resp.parsed_data

            commits_resp = await self.github_client.rest.repos.async_list_commits(
                owner=owner, repo=repo_name, per_page=20
            )
            commits = []
            for commit in commits_resp.parsed_data:
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
                        "files_changed": [],
                    }
                )

            prs_resp = await self.github_client.rest.pulls.async_list(
                owner=owner, repo=repo_name, state="all", per_page=20
            )
            open_prs = []
            for pr in prs_resp.parsed_data:
                open_prs.append(
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "user": pr.user.login if pr.user else "Unknown",
                        "created_at": pr.created_at.isoformat(),
                        "labels": [label.name for label in pr.labels],
                    }
                )

            issues_resp = await self.github_client.rest.issues.async_list_for_repo(
                owner=owner, repo=repo_name, state="all", per_page=20
            )
            recent_issues = []
            for issue in issues_resp.parsed_data:
                if not issue.pull_request:
                    recent_issues.append(
                        {
                            "number": issue.number,
                            "title": issue.title,
                            "state": issue.state,
                            "labels": [label.name for label in issue.labels],
                            "created_at": issue.created_at.isoformat(),
                            "body": (issue.body[:500] if issue.body else ""),
                        }
                    )

            languages_resp = await self.github_client.rest.repos.async_list_languages(
                owner=owner, repo=repo_name
            )
            languages = languages_resp.parsed_data

            key_files = await self._get_key_files_structure(owner, repo_name)

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
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            return context

        except GitHubException as e:
            logger.error(f"GitHub API error for {full_name}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting context for {full_name}: {e}")
            return {}

    async def _analyze_single_commit(self, owner: str, repo_name: str, commit) -> Dict:
        try:
            commit_data = {
                "sha": commit.sha[:8],
                "message": commit.commit.message,
                "author": commit.author.login if commit.author else "Unknown",
                "date": commit.commit.author.date.isoformat(),
                "files": [],
                "stats": {
                    "additions": (
                        getattr(commit.stats, "additions", 0)
                        if hasattr(commit, "stats")
                        else 0
                    ),
                    "deletions": (
                        getattr(commit.stats, "deletions", 0)
                        if hasattr(commit, "stats")
                        else 0
                    ),
                    "total": (
                        getattr(commit.stats, "total", 0)
                        if hasattr(commit, "stats")
                        else 0
                    ),
                },
            }

            try:
                commit_detail_resp = (
                    await self.github_client.rest.repos.async_get_commit(
                        owner=owner, repo=repo_name, ref=commit.sha
                    )
                )
                commit_detail = commit_detail_resp.parsed_data

                for file in commit_detail.files or []:
                    file_info = {
                        "filename": getattr(file, "filename", ""),
                        "status": getattr(file, "status", ""),
                        "additions": getattr(file, "additions", 0),
                        "deletions": getattr(file, "deletions", 0),
                        "changes": getattr(file, "changes", 0),
                        "patch": (
                            file.patch[:1000]
                            if hasattr(file, "patch") and file.patch
                            else None
                        ),
                    }

                    file_info.update(self._analyze_file_changes(file))
                    commit_data["files"].append(file_info)
            except Exception:
                pass

            return commit_data

        except Exception as e:
            logger.warning(f"Error analyzing commit {commit.sha}: {str(e)}")
            return {"sha": commit.sha[:8], "error": str(e)}

    def _analyze_file_changes(self, file) -> Dict:
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

        for line in added_lines:
            line = line.strip()

            if self._contains_security_risk(line):
                analysis["issues"].append(f"Security risk: {line[:50]}...")
                analysis["risk_level"] = "high"

            elif self._contains_performance_risk(line):
                analysis["issues"].append(f"Performance risk: {line[:50]}...")
                if analysis["risk_level"] == "low":
                    analysis["risk_level"] = "medium"

        if file.changes > 100:
            analysis["issues"].append(f"Large change: {file.changes} lines modified")
            if analysis["risk_level"] == "low":
                analysis["risk_level"] = "medium"

        return analysis

    def _analyze_commit_patterns(self, commits) -> Dict:
        patterns = {
            "commit_frequency": len(commits),
            "message_patterns": [],
            "time_patterns": [],
            "size_patterns": [],
        }

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
        risks = []

        if commit_data["stats"]["total"] > 200:
            risks.append(f"Large commit: {commit_data['stats']['total']} lines changed")

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

        critical_files = 0
        for file_info in commit_data.get("files", []):
            if file_info.get("is_critical_file"):
                critical_files += 1

        if critical_files > 0:
            risks.append(f"Modified {critical_files} critical files")

        return risks

    def _detect_language(self, filename: str) -> str:
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
        critical_patterns = [
            r"\.env",
            r"config\.(py|js|json|yaml|yml)",
            r"settings\.(py|js)",
            r"Dockerfile",
            r"docker-compose\.ya?ml",
            r"package\.json",
            r"requirements\.txt",
            r"Makefile",
            r"\.github/workflows/",
            r"\.gitlab-ci\.ya?ml",
            r"migrations?/",
            r"schema\.(sql|py|js)",
            r"models\.(py|js)",
            r"auth\.(py|js)",
            r"security\.(py|js)",
            r"middleware\.(py|js)",
            r"main\.(py|js)",
            r"app\.(py|js)",
            r"server\.(py|js)",
            r"index\.(py|js|html)",
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
        security_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_?key\s*=\s*["\'][^"\']+["\']',
            r"exec\s*\(",
            r"eval\s*\(",
            r"subprocess\.",
            r"shell\s*=\s*True",
            r"\.innerHTML\s*=",
            r"document\.write\s*\(",
            r"sql.*\+.*\+",
        ]

        for pattern in security_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True

        return False

    def _contains_performance_risk(self, line: str) -> bool:
        performance_patterns = [
            r"for.*in.*for.*in",
            r"while.*while",
            r"\.sync\(",
            r"time\.sleep\(",
            r"\.all\(\)\.count\(\)",
            r"SELECT \* FROM",
            r"setTimeout.*setTimeout",
            r"setInterval",
        ]

        for pattern in performance_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True

        return False

    def _correlate_logs_with_commits(self, logs: str, commits: List[Dict]) -> Dict:
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

            commit_message = commit.get("message", "").lower()
            for error_line in error_lines:
                if any(
                    word in commit_message
                    for word in error_line.split()
                    if len(word) > 3
                ):
                    commit_score += 2
                    matching_reasons.append(
                        f"Commit message relates to error: {error_line[:50]}..."
                    )

            for file_info in commit.get("files", []):
                filename = file_info.get("filename", "")
                if filename and filename.lower() in logs.lower():
                    commit_score += 3
                    matching_reasons.append(
                        f"Modified file appears in logs: {filename}"
                    )
                    correlation["related_files"].append(filename)

            if file_info.get("risk_level") == "high":
                commit_score += 2
                matching_reasons.append("High-risk code changes detected")

            if commit_score > 0:
                correlation["likely_culprits"].append(
                    {
                        "commit": commit,
                        "confidence_score": min(commit_score * 10, 100),
                        "reasons": matching_reasons,
                    }
                )

        correlation["likely_culprits"].sort(
            key=lambda x: x["confidence_score"], reverse=True
        )

        return correlation

    def _assess_overall_risk(self, commit_analysis: Dict) -> Dict:
        risk_assessment = {"level": "low", "score": 0, "factors": []}

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

        risk_indicators = commit_analysis.get("risk_indicators", [])
        risk_assessment["score"] += len(risk_indicators)
        risk_assessment["factors"].extend(risk_indicators)

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

        if risk_assessment["score"] >= 8:
            risk_assessment["level"] = "high"
        elif risk_assessment["score"] >= 4:
            risk_assessment["level"] = "medium"

        return risk_assessment

    def _suggest_focus_areas(
        self, commit_analysis: Dict, correlation: Dict
    ) -> List[str]:
        suggestions = []

        culprits = correlation.get("likely_culprits", [])
        if culprits:
            top_culprit = culprits[0]
            suggestions.append(
                f"Review commit {top_culprit['commit']['sha']} "
                f"(confidence: {top_culprit['confidence_score']}%)"
            )

        file_changes = commit_analysis.get("file_changes", {})
        if file_changes:
            most_changed = max(file_changes.items(), key=lambda x: x[1])
            if most_changed[1] > 1:
                suggestions.append(
                    f"Focus on {most_changed[0]} (changed {most_changed[1]} times)"
                )

        risk_indicators = commit_analysis.get("risk_indicators", [])
        high_risk_indicators = [
            r for r in risk_indicators if "high" in r.lower() or "critical" in r.lower()
        ]
        if high_risk_indicators:
            suggestions.append(
                "Review high-risk changes: " + "; ".join(high_risk_indicators[:2])
            )

        commits = commit_analysis.get("commits", [])
        large_commits = [c for c in commits if c.get("stats", {}).get("total", 0) > 100]
        if large_commits:
            suggestions.append(
                f"Review large recent commits: {len(large_commits)} commits with >100 lines changed"
            )

        return suggestions

    async def _get_full_repository_code(
        self, full_name: str, max_file_size: int = 50000
    ) -> Dict:
        try:
            owner, repo_name = full_name.split("/")
            repo_resp = await self.github_client.rest.repos.async_get(
                owner=owner, repo=repo_name
            )
            repo = repo_resp.parsed_data

            default_branch = repo.default_branch

            tree_resp = await self.github_client.rest.git.async_get_tree(
                owner=owner, repo=repo_name, tree_sha=default_branch, recursive=True
            )
            tree = tree_resp.parsed_data

            codebase = {
                "repository": full_name,
                "branch": default_branch,
                "files": {},
                "structure": [],
                "total_files": 0,
                "total_size": 0,
            }

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

            code_files = []
            for element in tree.tree:
                if element.type == "blob":
                    file_path = element.path
                    file_ext = (
                        "." + file_path.split(".")[-1].lower()
                        if "." in file_path
                        else ""
                    )

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

            code_files.sort(
                key=lambda f: self._get_file_importance_score(f["path"]), reverse=True
            )

            total_content_size = 0
            max_total_size = 200000

            for file_info in code_files:
                if total_content_size >= max_total_size:
                    break

                if file_info["size"] > max_file_size:
                    codebase["files"][file_info["path"]] = {
                        "content": f"[File too large: {file_info['size']} bytes]",
                        "size": file_info["size"],
                        "extension": file_info["extension"],
                        "truncated": True,
                    }
                    continue

                try:
                    content_resp = (
                        await self.github_client.rest.repos.async_get_content(
                            owner=owner, repo=repo_name, path=file_info["path"]
                        )
                    )
                    file_content = content_resp.parsed_data

                    if hasattr(file_content, "content") and file_content.content:
                        import base64

                        decoded_content = base64.b64decode(file_content.content).decode(
                            "utf-8", errors="ignore"
                        )

                        if total_content_size + len(decoded_content) > max_total_size:
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
        directories = set()

        for path in file_paths:
            parts = path.split("/")
            for i in range(len(parts)):
                dir_path = "/".join(parts[: i + 1])
                directories.add(dir_path)

        return sorted(list(directories))


github_service = GitHubService()
