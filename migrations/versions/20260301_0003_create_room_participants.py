"""create room participants

Revision ID: 20260301_0003
Revises: 20260301_0002
Create Date: 2026-03-02 10:45:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260301_0003"
down_revision: Union[str, Sequence[str], None] = "20260301_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "room_participants" not in tables:
        op.create_table(
            "room_participants",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("room", sa.String(), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("joined_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("room", "username", name="uq_room_username"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_room_participants_room ON room_participants (room)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_room_participants_username ON room_participants (username)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_room_participants_is_online ON room_participants (is_online)"
    )


def downgrade() -> None:
    op.drop_index("ix_room_participants_is_online", table_name="room_participants")
    op.drop_index("ix_room_participants_username", table_name="room_participants")
    op.drop_index("ix_room_participants_room", table_name="room_participants")
    op.drop_table("room_participants")
