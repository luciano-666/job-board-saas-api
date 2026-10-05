"""add composite indexes for application cursor pagination

Revision ID: c012762d8cda
Revises: 05ca0c5104e9
Create Date: 2026-09-27 22:41:07.399994

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c012762d8cda"
down_revision: Union[str, Sequence[str], None] = "05ca0c5104e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_applications_job_id_created_at_id",
        "job_board_applications",
        ["job_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_applications_candidate_id_created_at_id",
        "job_board_applications",
        ["candidate_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_applications_candidate_id_created_at_id",
        table_name="job_board_applications",
    )
    op.drop_index(
        "ix_applications_job_id_created_at_id", table_name="job_board_applications"
    )
