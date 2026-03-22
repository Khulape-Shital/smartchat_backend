"""Add user_id to document_chunks for ownership-based access control.

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column to document_chunks table
    op.add_column(
        'document_chunks',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()'))
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_document_chunks_user_id',
        'document_chunks',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on (user_id, chat_id) for efficient filtering
    op.create_index(
        'idx_document_chunks_user_chat',
        'document_chunks',
        ['user_id', 'chat_id']
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_document_chunks_user_chat', table_name='document_chunks')
    
    # Drop foreign key constraint
    op.drop_constraint(
        'fk_document_chunks_user_id',
        'document_chunks',
        type_='foreignkey'
    )
    
    # Drop column
    op.drop_column('document_chunks', 'user_id')
