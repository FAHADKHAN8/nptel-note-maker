"""lecture external ids

Revision ID: 0005_lecture_external_ids
Revises: 0004_course_artifacts
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_lecture_external_ids"
down_revision = "0004_course_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lectures", sa.Column("external_unit_id", sa.String(80), nullable=True))
    op.add_column("lectures", sa.Column("external_lesson_id", sa.String(80), nullable=True))
    op.create_index("ix_lectures_external_unit_id", "lectures", ["external_unit_id"])
    op.create_index("ix_lectures_external_lesson_id", "lectures", ["external_lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_lectures_external_lesson_id", table_name="lectures")
    op.drop_index("ix_lectures_external_unit_id", table_name="lectures")
    op.drop_column("lectures", "external_lesson_id")
    op.drop_column("lectures", "external_unit_id")
