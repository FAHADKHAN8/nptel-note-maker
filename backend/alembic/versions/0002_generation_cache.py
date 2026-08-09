"""generation cache metadata

Revision ID: 0002_generation_cache
Revises: 0001_initial
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_generation_cache"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transcripts", sa.Column("content_hash", sa.String(64), nullable=True))
    op.create_index("ix_transcripts_content_hash", "transcripts", ["content_hash"])
    op.add_column("notes", sa.Column("source_transcript_hash", sa.String(64), nullable=True))
    op.add_column("notes", sa.Column("generation_settings_hash", sa.String(64), nullable=True))
    op.create_index("ix_notes_source_transcript_hash", "notes", ["source_transcript_hash"])
    op.create_index("ix_notes_generation_settings_hash", "notes", ["generation_settings_hash"])
    op.create_table(
        "generated_chunk_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lecture_id", sa.Integer(), sa.ForeignKey("lectures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_hash", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(80), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("generated_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("lecture_id", "chunk_index", "chunk_hash", "prompt_version", "model_name", name="uq_generated_chunk_cache_key"),
    )
    op.create_index("ix_generated_chunk_cache_lecture_id", "generated_chunk_cache", ["lecture_id"])
    op.create_index("ix_generated_chunk_cache_chunk_hash", "generated_chunk_cache", ["chunk_hash"])
    op.create_index("ix_generated_chunk_cache_prompt_version", "generated_chunk_cache", ["prompt_version"])
    op.create_index("ix_generated_chunk_cache_model_name", "generated_chunk_cache", ["model_name"])


def downgrade() -> None:
    op.drop_index("ix_generated_chunk_cache_model_name", table_name="generated_chunk_cache")
    op.drop_index("ix_generated_chunk_cache_prompt_version", table_name="generated_chunk_cache")
    op.drop_index("ix_generated_chunk_cache_chunk_hash", table_name="generated_chunk_cache")
    op.drop_index("ix_generated_chunk_cache_lecture_id", table_name="generated_chunk_cache")
    op.drop_table("generated_chunk_cache")
    op.drop_index("ix_notes_generation_settings_hash", table_name="notes")
    op.drop_index("ix_notes_source_transcript_hash", table_name="notes")
    op.drop_column("notes", "generation_settings_hash")
    op.drop_column("notes", "source_transcript_hash")
    op.drop_index("ix_transcripts_content_hash", table_name="transcripts")
    op.drop_column("transcripts", "content_hash")
