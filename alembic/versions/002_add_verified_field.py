"""Add verified field to users table.

Revision ID: 002
Revises: 001
Create Date: 2026-03-21 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add verified column to users table
    op.add_column('users', sa.Column('verified', sa.String(5), nullable=False, server_default='False'))


def downgrade() -> None:
    # Remove verified column from users table
    op.drop_column('users', 'verified')
