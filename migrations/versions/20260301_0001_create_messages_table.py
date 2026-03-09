"""create messages table

Revision ID: 20260301_0001
Revises:
Create Date: 2026-03-01 17:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260301_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "messages" in tables:
        op.execute("CREATE INDEX IF NOT EXISTS ix_messages_room ON messages (room)")
        return

    if "message" in tables:
        op.rename_table("message", "messages")
        op.execute("CREATE INDEX IF NOT EXISTS ix_messages_room ON messages (room)")
        return

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room", sa.String(), nullable=False),
        sa.Column("sender", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_room", "messages", ["room"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_room", table_name="messages")
    op.drop_table("messages")
