import redis
import logging
from fastapi import HTTPException, status
from app.core.constants import SESSION_LIMIT, EXPIRY_SECONDS

logger = logging.getLogger(__name__)

 
redis_available = False
r = None
try:
    r = redis.Redis(
        host="localhost", 
        port=6379, 
        decode_responses=True, 
        socket_connect_timeout=1, 
        socket_timeout=1,
    )
    # Don't test on startup - test lazily when actually used
    redis_available = True
except Exception as e:
    logger.warning(f"Redis initialization failed: {e}. Rate limiting will be disabled.")

def session_limiter(chat_id: str):
    """
    Rate limit messages per session.
    Raises HTTP 429 if SESSION_LIMIT is exceeded within EXPIRY_SECONDS.
    Silently skips limiting if Redis is unavailable (degrades gracefully).
    """
    # Skip limiting if Redis is not available
    if not redis_available or r is None:
        return
    
    try:
        key = f"session:{chat_id}"

        
        new_count = r.incr(key)
        
        # Set expiry on first increment
        if new_count == 1:
            r.expire(key, EXPIRY_SECONDS)
        
        # Check limit after increment (atomic safe)
        if new_count > SESSION_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Session message limit reached"
            )
    except HTTPException:
        # Re-raise HTTP exceptions (rate limit exceeded)
        raise
    except Exception as e:
        # Log Redis errors but don't block the request
        logger.warning(f"Redis session limiting error: {e}. Allowing request to proceed.")
        # Gracefully degrade - allow request if Redis is down
        return