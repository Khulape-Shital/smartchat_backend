"""Unified models file to avoid circular imports."""
from __future__ import annotations

from sqlalchemy import Column, String, Text, ForeignKey, BIGINT, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.time_utils import get_unix_timestamp
from app.db.session import Base
from pgvector.sqlalchemy import Vector


class User(Base):
    """User model for storing user account information."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password = Column(String(255), nullable=True)
    google_id = Column(String(255), nullable=True, unique=True)
    profile_picture = Column(Text, nullable=True)
    created_at = Column(BIGINT)


class ChatSession(Base):
    """Chat session model for storing conversation threads."""
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255))
    created_at = Column(BIGINT)
    updated_at = Column(BIGINT)


class Message(Base):
    """Message model for storing individual messages in a chat session."""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=True)
    file = Column(String(255), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(100), nullable=True)
    feedback = Column(String(10), nullable=True)
    created_at = Column(BIGINT)
    updated_at = Column(BIGINT)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="check_role"),
        CheckConstraint("feedback IN ('like', 'dislike') OR feedback IS NULL", name="check_feedback"),
    )


class DocumentChunk(Base):
    """Document chunk model for storing RAG embeddings and content."""
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384))
    created_at = Column(BIGINT)
