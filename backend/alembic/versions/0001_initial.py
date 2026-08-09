"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("courses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(300), nullable=False), sa.Column("description", sa.Text()), sa.Column("instructor", sa.String(200)), sa.Column("institute", sa.String(200)), sa.Column("source_url", sa.String(1000), nullable=False, unique=True), sa.Column("thumbnail_url", sa.String(1000)), sa.Column("total_weeks", sa.Integer(), nullable=False), sa.Column("total_lectures", sa.Integer(), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("lectures", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False), sa.Column("week_number", sa.Integer(), nullable=False), sa.Column("lecture_number", sa.Integer(), nullable=False), sa.Column("title", sa.String(300), nullable=False), sa.Column("nptel_url", sa.String(1000)), sa.Column("youtube_url", sa.String(1000)), sa.Column("youtube_video_id", sa.String(20)), sa.Column("duration_seconds", sa.Integer()), sa.Column("status", sa.String(40), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_lectures_course_id", "lectures", ["course_id"])
    op.create_index("ix_lectures_youtube_video_id", "lectures", ["youtube_video_id"])
    op.create_table("processing_jobs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE")), sa.Column("lecture_id", sa.Integer(), sa.ForeignKey("lectures.id", ondelete="CASCADE")), sa.Column("job_type", sa.String(80), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("progress", sa.Integer(), nullable=False), sa.Column("message", sa.String(500)), sa.Column("error_message", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("started_at", sa.DateTime()), sa.Column("completed_at", sa.DateTime()))
    op.create_table("transcripts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("lecture_id", sa.Integer(), sa.ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("source", sa.String(40), nullable=False), sa.Column("language", sa.String(20), nullable=False), sa.Column("raw_text", sa.Text(), nullable=False), sa.Column("cleaned_text", sa.Text(), nullable=False), sa.Column("segments_json", sa.JSON(), nullable=False), sa.Column("character_count", sa.Integer(), nullable=False), sa.Column("word_count", sa.Integer(), nullable=False), sa.Column("source_url", sa.String(1000)), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("notes", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("lecture_id", sa.Integer(), sa.ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("title", sa.String(300), nullable=False), sa.Column("content_markdown", sa.Text(), nullable=False), sa.Column("generation_style", sa.String(40), nullable=False), sa.Column("model_name", sa.String(120)), sa.Column("prompt_version", sa.String(40), nullable=False), sa.Column("is_user_edited", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))


def downgrade() -> None:
    op.drop_table("notes")
    op.drop_table("transcripts")
    op.drop_table("processing_jobs")
    op.drop_index("ix_lectures_youtube_video_id", table_name="lectures")
    op.drop_index("ix_lectures_course_id", table_name="lectures")
    op.drop_table("lectures")
    op.drop_table("courses")
