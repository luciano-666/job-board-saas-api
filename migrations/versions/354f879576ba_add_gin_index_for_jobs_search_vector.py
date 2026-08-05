"""add gin index for jobs search vector

Revision ID: 354f879576ba
Revises: 68c47c16c50b
Create Date: 2026-07-30 05:57:02.479401

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "354f879576ba"
down_revision: Union[str, Sequence[str], None] = "68c47c16c50b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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
