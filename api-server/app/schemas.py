import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models import DeploymentStatus


class ProjectCreate(BaseModel):
    name: str
    git_url: str

    @field_validator("git_url")
    @classmethod
    def must_look_like_a_repo(cls, v: str) -> str:
        if not (v.startswith("https://") or v.startswith("git@")):
            raise ValueError("git_url must be an https:// or git@ URL")
        return v


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    git_url: str
    subdomain: str
    created_at: datetime


class DeploymentRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: DeploymentStatus
    ecs_task_arn: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class DeploymentStatusUpdate(BaseModel):
    status: DeploymentStatus
    error: str | None = None
