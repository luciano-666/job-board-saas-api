"""make sessions referrer column nullable

Revision ID: 946de6469907
Revises: 9403ab33f34f
Create Date: 2026-08-10 11:02:38.196659

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "946de6469907"
down_revision: Union[str, Sequence[str], None] = "9403ab33f34f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "job_board_sessions",
        "referrer",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "job_board_sessions",
        "referrer",
        existing_type=sa.String(length=255),
        nullable=False,
    )
