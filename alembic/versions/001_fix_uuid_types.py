"""Fix UUID column types in chat_sessions and messages tables.

Revision ID: 001
Revises: 
Create Date: 2026-03-21 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert user_id column from VARCHAR to UUID in chat_sessions
    op.execute('ALTER TABLE chat_sessions ALTER COLUMN user_id TYPE UUID USING user_id::uuid')
    
    # Convert chat_id column from VARCHAR to UUID in chat_messages
    op.execute('ALTER TABLE chat_messages ALTER COLUMN chat_id TYPE UUID USING chat_id::uuid')


def downgrade() -> None:
    # Revert user_id back to VARCHAR in chat_sessions
    op.execute('ALTER TABLE chat_sessions ALTER COLUMN user_id TYPE VARCHAR(255) USING user_id::varchar')
    
    # Revert chat_id back to VARCHAR in chat_messages
    op.execute('ALTER TABLE chat_messages ALTER COLUMN chat_id TYPE VARCHAR(255) USING chat_id::varchar')
