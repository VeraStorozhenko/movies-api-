"""add token expiration and refresh tokens

Revision ID: 20260302_0005
Revises: 20260302_0004
Create Date: 2026-03-02 11:45:00

"""
from datetime import datetime, timedelta, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260302_0005"
down_revision: Union[str, Sequence[str], None] = "20260302_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    token_columns = {c["name"] for c in inspector.get_columns("auth_tokens")}
    if "expires_at" not in token_columns:
        with op.batch_alter_table("auth_tokens") as batch_op:
            batch_op.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))

        expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
        op.execute(
            sa.text("UPDATE auth_tokens SET expires_at = :expiry WHERE expires_at IS NULL").bindparams(
                expiry=expiry
            )
        )

        with op.batch_alter_table("auth_tokens") as batch_op:
            batch_op.alter_column("expires_at", nullable=False)

    tables = set(inspector.get_table_names())
    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token ON refresh_tokens (token)")


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    with op.batch_alter_table("auth_tokens") as batch_op:
        batch_op.drop_column("expires_at")
