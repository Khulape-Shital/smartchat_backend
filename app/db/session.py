from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings
 
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

 
class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()