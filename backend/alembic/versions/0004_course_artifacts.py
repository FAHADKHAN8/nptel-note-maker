"""course synthesis artifacts

Revision ID: 0004_course_artifacts
Revises: 0003_course_processing_jobs
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_course_artifacts"
down_revision = "0003_course_processing_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "course_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(40), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("course_id", "artifact_type", "week_number", name="uq_course_artifact_scope"),
    )
    op.create_index("ix_course_artifacts_course_id", "course_artifacts", ["course_id"])
    op.create_index("ix_course_artifacts_artifact_type", "course_artifacts", ["artifact_type"])
    op.create_index("ix_course_artifacts_source_hash", "course_artifacts", ["source_hash"])


def downgrade() -> None:
    op.drop_index("ix_course_artifacts_source_hash", table_name="course_artifacts")
    op.drop_index("ix_course_artifacts_artifact_type", table_name="course_artifacts")
    op.drop_index("ix_course_artifacts_course_id", table_name="course_artifacts")
    op.drop_table("course_artifacts")
