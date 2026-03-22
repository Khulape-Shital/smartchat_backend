from sqlalchemy import Column, String, Text, ForeignKey, BIGINT, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.time_utils import get_unix_timestamp
import uuid
from app.db.session import Base
from pgvector.sqlalchemy import Vector


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), default="New Chat", nullable=False)
    created_at = Column(BIGINT, default=get_unix_timestamp)
    updated_at = Column(BIGINT, default=get_unix_timestamp, onupdate=get_unix_timestamp)
    messages = relationship("Message", back_populates="chat", cascade="all,delete-orphan")
    user = relationship("User", back_populates="sessions")

class Message(Base):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)

 
    role = Column(String(20), CheckConstraint("role IN ('user', 'assistant')"), nullable=False)

     
    message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=True)

     
    file = Column(String(255), nullable=True)  # Path to uploaded file
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(100), nullable=True)
 
    feedback = Column(String(10), CheckConstraint("feedback IN ('like', 'dislike')"), nullable=True)
    created_at = Column(BIGINT, default=get_unix_timestamp)
    updated_at = Column(BIGINT, default=get_unix_timestamp , onupdate=get_unix_timestamp)

    chat = relationship("ChatSession", back_populates="messages")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

  
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    content = Column(Text, nullable=False)

     
    embedding = Column(Vector(384))  # if using MiniLM

    created_at = Column(BIGINT, default=get_unix_timestamp)