from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class GitHubRepository(BaseModel):
    id: Optional[UUID] = None
    org_name: str
    repo_name: str
    full_name: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    webhook_secret: Optional[str] = None
    team_id: Optional[UUID] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GitHubRepositoryCreate(BaseModel):
    org_name: str
    repo_name: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    team_id: Optional[UUID] = None


class GitHubRepositoryUpdate(BaseModel):
    description: Optional[str] = None
    primary_language: Optional[str] = None
    team_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class CIFailure(BaseModel):
    id: Optional[UUID] = None
    repo_id: UUID
    workflow_name: str
    commit_sha: str
    branch_name: str
    failure_reason: str
    logs: Optional[str] = None
    ticket_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CIFailureCreate(BaseModel):
    repo_id: str
    workflow_name: str
    commit_sha: str
    branch_name: str
    failure_reason: str
    logs: Optional[str] = None


class RepositoryContext(BaseModel):
    id: Optional[UUID] = None
    repo_id: UUID
    context_type: str
    context_data: dict
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GitHubWebhookPayload(BaseModel):
    action: Optional[str] = None
    repository: dict
    workflow_run: Optional[dict] = None
    workflow_job: Optional[dict] = None
    sender: dict
    zen: Optional[str] = None
