"""p1 hardening: index job_listings.source_url

Revision ID: 6df16cfd582e
Revises: 47a7b037d259
Create Date: 2026-04-11 11:26:49.075476

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6df16cfd582e"
down_revision: Union[str, Sequence[str], None] = "47a7b037d259"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add index on job_listings.source_url for import-dedup lookups."""
    with op.batch_alter_table("job_listings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_job_listings_source_url"),
            ["source_url"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("job_listings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_job_listings_source_url"))
