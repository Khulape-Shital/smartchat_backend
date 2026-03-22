"""Main application entry point."""
import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.api import api_router
from app.core.config import settings
from app.db.session import engine, Base, get_db
from app.core.constants import (
    APP_TITLE, APP_VERSION, APP_DESCRIPTION,
    MEDIA_DIR, CHAT_FILES_SUBDIR,
)
from app.utils.rag import initialize_embeddings_model
 
logger = logging.getLogger(__name__)

# [CRITICAL] create_all is a dev shortcut and is unsafe in production.
# It never alters or drops existing columns on schema drift.
# SUGGESTION: Remove this line and rely exclusively on Alembic migrations.
# Run: alembic upgrade head on deployment.
# Base.metadata.create_all(bind=engine)  # REMOVED -- use Alembic migrations

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Lifespan handler to load embedding model at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up: Loading embedding model...")
    try:
        initialize_embeddings_model()
        logger.info("✅ Embedding model loaded successfully at startup")
    except Exception as e:
        logger.error(f"❌ Failed to load embedding model at startup: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# [CRITICAL] CORS origins are hardcoded constants, not environment-driven.
# allow_credentials=True combined with broad origins is a security misconfiguration.
# SUGGESTION: Load allowed origins from settings (environment variable) and restrict
# to the exact deployed frontend origin in production.
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API router with /api prefix
app.include_router(api_router, prefix="/api")


# [LOW] No /health endpoint. A GET /health that also pings the DB is essential
# for load balancers, container orchestration, and monitoring systems.
# SUGGESTION: Add @app.get("/health") that checks DB connectivity and returns status.
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies database connectivity.
    Returns 200 if healthy, 503 if database is unreachable.
    """
    try:
        # Simple query to test DB connectivity
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "message": "SmartChat API is operational"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
            },
        )



@app.get("/")
async def root():
    return {
        "message": "SmartChat FastAPI Backend",
          "status": "running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)