"""course processing job metadata

Revision ID: 0003_course_processing_jobs
Revises: 0002_generation_cache
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_course_processing_jobs"
down_revision = "0002_generation_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("course_code", sa.String(80), nullable=True))
    op.create_index("ix_courses_course_code", "courses", ["course_code"])
    op.add_column("lectures", sa.Column("transcript_url", sa.String(1000), nullable=True))
    op.add_column("lectures", sa.Column("error_message", sa.String(1000), nullable=True))
    op.add_column("processing_jobs", sa.Column("stage", sa.String(80), nullable=True))
    op.add_column("processing_jobs", sa.Column("total_lectures", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("processing_jobs", sa.Column("completed_lectures", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("processing_jobs", sa.Column("failed_lectures", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("processing_jobs", sa.Column("current_lecture_id", sa.Integer(), nullable=True))
    op.add_column("processing_jobs", sa.Column("current_lecture_title", sa.String(300), nullable=True))
    op.add_column("processing_jobs", sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("processing_jobs", "updated_at")
    op.drop_column("processing_jobs", "current_lecture_title")
    op.drop_column("processing_jobs", "current_lecture_id")
    op.drop_column("processing_jobs", "failed_lectures")
    op.drop_column("processing_jobs", "completed_lectures")
    op.drop_column("processing_jobs", "total_lectures")
    op.drop_column("processing_jobs", "stage")
    op.drop_column("lectures", "error_message")
    op.drop_column("lectures", "transcript_url")
    op.drop_index("ix_courses_course_code", table_name="courses")
    op.drop_column("courses", "course_code")
