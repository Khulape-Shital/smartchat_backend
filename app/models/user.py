from sqlalchemy import Column,String,Text,BIGINT, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.session import Base
from app.core.time_utils import get_unix_timestamp

class User(Base):
    __tablename__= "users"

 
    id = Column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
 
    email= Column(String(255), unique=True, nullable=False, index=True)  

    name = Column(String(255) ,nullable=False)
    password = Column(String(255), nullable=True)
    google_id = Column(String(255), nullable=True, unique=True)
    profile_picture = Column(Text,nullable=True)
    verified = Column(String(5), default="False", nullable=False)
 
    created_at = Column(BIGINT, default=get_unix_timestamp, server_default=func.extract('epoch', func.now()).cast(BIGINT))

    
    sessions = relationship("ChatSession", back_populates="user", cascade="all,delete-orphan")