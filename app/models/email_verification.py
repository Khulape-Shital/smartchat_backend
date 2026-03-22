from sqlalchemy import Column, String, BIGINT, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.session import Base
from app.core.time_utils import get_unix_timestamp


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    created_at = Column(BIGINT, default=get_unix_timestamp)
    expires_at = Column(BIGINT, nullable=False)
    verified_at = Column(BIGINT, nullable=True)  # Timestamp when email was verified, None if not yet verified

    user = relationship("User", foreign_keys=[user_id])
