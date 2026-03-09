"""add recipient to messages

Revision ID: 20260301_0002
Revises: 20260301_0001
Create Date: 2026-03-01 18:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260301_0002"
down_revision: Union[str, Sequence[str], None] = "20260301_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("messages")}

    if "recipient" not in columns:
        with op.batch_alter_table("messages") as batch_op:
            batch_op.add_column(sa.Column("recipient", sa.String(), nullable=True))

    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_recipient ON messages (recipient)")


def downgrade() -> None:
    op.drop_index("ix_messages_recipient", table_name="messages")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_column("recipient")
