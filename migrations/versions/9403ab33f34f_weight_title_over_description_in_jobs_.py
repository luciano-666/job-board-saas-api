"""weight title over description in jobs search vector

Revision ID: 9403ab33f34f
Revises: 354f879576ba
Create Date: 2026-07-30 06:55:52.268517

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9403ab33f34f"
down_revision: Union[str, Sequence[str], None] = "354f879576ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass  # Generated columns cannot be altered in-place in Postgres — drop and
    # recreate with weighted setweight() so title matches rank higher than
    # description matches.
    op.drop_index("ix_jobs_search_vector_gin", table_name="job_board_jobs")
    op.drop_column("job_board_jobs", "search_vector")

    op.add_column(
        "job_board_jobs",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
                "setweight(to_tsvector('english', coalesce(description, '')), 'B')",
                persisted=True,
            ),
            nullable=True,
            comment="Full-text search vector, title weighted above description",
        ),
    )

    op.create_index(
        "ix_jobs_search_vector_gin",
        "job_board_jobs",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_jobs_search_vector_gin", table_name="job_board_jobs")
    op.drop_column("job_board_jobs", "search_vector")

    op.add_column(
        "job_board_jobs",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_jobs_search_vector_gin",
        "job_board_jobs",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )
