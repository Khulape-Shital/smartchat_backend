"""Add refresh token blacklist table for token revocation.

Revision ID: 003
Revises: 002
Create Date: 2026-03-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create refresh_token_blacklist table
    op.create_table(
        'refresh_token_blacklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('jti', sa.String(255), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('revoked_at', sa.BIGINT(), nullable=False),
        sa.Column('expires_at', sa.BIGINT(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti')
    )
    # Create indexes
    op.create_index('idx_blacklist_user_jti', 'refresh_token_blacklist', ['user_id', 'jti'])
    op.create_index(op.f('ix_refresh_token_blacklist_jti'), 'refresh_token_blacklist', ['jti'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_refresh_token_blacklist_jti'), table_name='refresh_token_blacklist')
    op.drop_index('idx_blacklist_user_jti', table_name='refresh_token_blacklist')
    # Drop table
    op.drop_table('refresh_token_blacklist')
