import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.ecs_client import run_build_task
from app.models import Deployment, DeploymentStatus, Project
from app.schemas import DeploymentRead, DeploymentStatusUpdate

router = APIRouter(tags=["deployments"])


@router.post("/projects/{project_id}/deploy", response_model=DeploymentRead, status_code=201)
def create_deployment(project_id: uuid.UUID, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    deployment = Deployment(project_id=project.id, status=DeploymentStatus.QUEUED)
    session.add(deployment)
    session.commit()
    session.refresh(deployment)

    try:
        task_arn = run_build_task(
            git_url=project.git_url,
            project_id=str(project.id),
            deployment_id=str(deployment.id),
        )
        deployment.status = DeploymentStatus.IN_PROGRESS
        deployment.ecs_task_arn = task_arn
    except Exception as exc:  # noqa: BLE001 — surface any RunTask failure onto the row
        deployment.status = DeploymentStatus.FAILED
        deployment.error = str(exc)

    deployment.updated_at = datetime.utcnow()
    session.add(deployment)
    session.commit()
    session.refresh(deployment)
    return deployment


@router.get("/deployments/{deployment_id}", response_model=DeploymentRead)
def get_deployment(deployment_id: uuid.UUID, session: Session = Depends(get_session)):
    deployment = session.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.get("/projects/{project_id}/deployments", response_model=list[DeploymentRead])
def list_deployments(project_id: uuid.UUID, session: Session = Depends(get_session)):
    return session.exec(
        select(Deployment).where(Deployment.project_id == project_id).order_by(Deployment.created_at.desc())
    ).all()


@router.patch("/deployments/{deployment_id}/status", response_model=DeploymentRead)
def update_deployment_status(
    deployment_id: uuid.UUID,
    payload: DeploymentStatusUpdate,
    session: Session = Depends(get_session),
):
    """The build-worker calls this (or writes directly to Postgres — see
    build-worker/README) when a build finishes or fails."""
    deployment = session.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment.status = payload.status
    deployment.error = payload.error
    deployment.updated_at = datetime.utcnow()
    session.add(deployment)
    session.commit()
    session.refresh(deployment)
    return deployment
