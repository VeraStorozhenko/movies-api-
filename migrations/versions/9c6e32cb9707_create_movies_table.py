"""create movies table

Revision ID: 9c6e32cb9707
Revises: 20260302_0005
Create Date: 2026-03-03 11:59:18.875458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = '9c6e32cb9707'
down_revision: Union[str, Sequence[str], None] = '20260302_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('movies', sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.add_column('movies', sa.Column('director', sqlmodel.sql.sqltypes.AutoString(), nullable=False))
    op.add_column('movies', sa.Column('year', sa.Integer(), nullable=False))
    op.add_column('movies', sa.Column('rating', sa.Integer(), nullable=False))


def downgrade() -> None:
    op.drop_column('movies', 'rating')
    op.drop_column('movies', 'year')
    op.drop_column('movies', 'director')
    op.drop_column('movies', 'description')