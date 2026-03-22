from sqlalchemy import Column, String, BIGINT, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.session import Base
from app.core.time_utils import get_unix_timestamp


class RefreshTokenBlacklist(Base):
    """
    Stores revoked refresh tokens to prevent reuse after logout or token rotation.
    Tokens are stored with their JTI (JWT ID) and expiration timestamp for cleanup.
    """
    __tablename__ = "refresh_token_blacklist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID from token
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    revoked_at = Column(BIGINT, default=get_unix_timestamp, nullable=False)
    expires_at = Column(BIGINT, nullable=False)  # Token expiration time for cleanup

    user = relationship("User", foreign_keys=[user_id])

    # Composite index for efficient queries: user_id + jti lookup
    __table_args__ = (
        Index('idx_blacklist_user_jti', 'user_id', 'jti'),
    )
