"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("git_url", sa.String(), nullable=False),
        sa.Column("subdomain", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_project_subdomain", "project", ["subdomain"], unique=True)

    op.create_table(
        "deployment",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("project.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("ecs_task_arn", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_deployment_project_id", "deployment", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_deployment_project_id", table_name="deployment")
    op.drop_table("deployment")
    op.drop_index("ix_project_subdomain", table_name="project")
    op.drop_table("project")
