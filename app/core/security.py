from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import uuid
import logging

from app.db.session import get_db
from app.models.user import User
from app.models.token_blacklist import RefreshTokenBlacklist
from app.core.config import settings
from app.core.constants import OAUTH2_TOKEN_URL, ERROR_COULD_NOT_VALIDATE, BCRYPT_SCHEMES, BCRYPT_DEPRECATED, PASSWORD_MAX_LEN

logger = logging.getLogger(__name__)
 
pwd_context = CryptContext(schemes=BCRYPT_SCHEMES, deprecated=BCRYPT_DEPRECATED)

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password[:PASSWORD_MAX_LEN])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password[:PASSWORD_MAX_LEN], hashed_password)

 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=OAUTH2_TOKEN_URL)
 
def _decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )

def create_access_token(user_id: str) -> str:
    """Create access token with expiration and JTI for revocation tracking."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid.uuid4())  # Unique token ID for revocation tracking
  
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "jti": jti
    }
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return token

def create_refresh_token(user_id: str) -> str:
    """Create refresh token with expiration and JTI for revocation tracking."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    jti = str(uuid.uuid4())  # Unique token ID for revocation tracking

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "jti": jti
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return token


def verify_refresh_token(refresh_token: str, db: Session = None):
    """Verify refresh token and check if it's blacklisted."""
    payload = _decode_token(refresh_token)
    
    user_id = payload.get("sub")
    token_type = payload.get("type")
    jti = payload.get("jti")

    # ensure this is a refresh token
    if user_id is None or token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if token is blacklisted (revoked)
    if db and jti:
        try:
            blacklisted = db.query(RefreshTokenBlacklist).filter(
                RefreshTokenBlacklist.jti == jti
            ).first()
            if blacklisted:
                logger.warning(f"Revoked token reuse attempt: JTI {jti}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
    
    return user_id


def delete_refresh_token(refresh_token: str, db: Session):
    """
    Revoke a refresh token by storing its JTI in the blacklist.
    Prevents token reuse after logout or token rotation.
    """
    if not db:
        logger.warning("Database session not provided for token revocation")
        return
    
    payload = _decode_token(refresh_token)
    jti = payload.get("jti")
    user_id = payload.get("sub")
    exp = payload.get("exp")
    
    if not jti or not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token structure"
        )
    
    # Check if token is already blacklisted
    existing = db.query(RefreshTokenBlacklist).filter(
        RefreshTokenBlacklist.jti == jti
    ).first()
    
    if existing:
        logger.info(f"Token JTI {jti} already blacklisted")
        return
    
    try:
        # Store token in blacklist
        blacklisted_token = RefreshTokenBlacklist(
            jti=jti,
            user_id=uuid.UUID(user_id),
            expires_at=int(exp) if exp else None
        )
        db.add(blacklisted_token)
        db.commit()
        logger.info(f"Token JTI {jti} revoked and stored in blacklist")
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing token in blacklist: {e}")
      

def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)

    ) -> User:
    
 
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERROR_COULD_NOT_VALIDATE,
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        payload = _decode_token(token)
        user_id: str = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception
        
        # Convert user_id string to UUID
        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid user_id format in token: {user_id}, error: {e}")
            raise credentials_exception
        
        # Query database for user
        try:
            user = db.query(User).filter(User.id == user_uuid).first()
        except Exception as e:
            logger.error(f"Database error when querying user {user_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error"
            )

        if user is None:
            logger.warning(f"User not found in database: {user_id}")
            raise credentials_exception
        
        return user
    except HTTPException:
        # Re-raise HTTP exceptions (401s, 500s, etc)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )
