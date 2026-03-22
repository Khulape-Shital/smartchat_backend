import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.models.email_verification import EmailVerificationToken
from app.schemas.user import( ForgotPasswordRequest, ResetPasswordRequest, UserCreate, UserLogin, AuthResponse,
UserResponse, GoogleAuth, ForgotPasswordResponse, ResetPasswordResponse, RefreshTokenResponse, VerifyEmailRequest, VerifyEmailResponse, RegisterResponse)
from app.core.config import settings
from app.core.security import (
    create_access_token, 
    create_refresh_token, 
    verify_refresh_token,
    delete_refresh_token,
    hash_password,
    verify_password
)
from app.core.time_utils import get_unix_timestamp
from app.utils.helpers import send_email
import smtplib
 
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer
from app.core.constants import (
    RESPONSE_MESSAGE,
    ERROR_INVALID_GOOGLE_TOKEN, 
    ERROR_USER_ALREADY_EXISTS, 
    ERROR_INVALID_CREDENTIALS,
)

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

 
@router.post("/google", response_model=AuthResponse)
@limiter.limit("10/minute")
async def google_auth(request: Request, auth_data: GoogleAuth, db: Session = Depends(get_db)):
    try:
        if not settings.GOOGLE_CLIENT_ID:
            logger.error(f"GOOGLE_CLIENT_ID not configured")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google auth not configured"
            )
        
        logger.info(f"Verifying Google token with CLIENT_ID: {settings.GOOGLE_CLIENT_ID[:20]}...")
        user_info = id_token.verify_oauth2_token(
            auth_data.token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        email = user_info["email"]
        name = user_info.get("name", "")
        google_id = user_info["sub"]
        picture = user_info.get("picture")
        logger.info(f"✅ Google token verified for: {email}")

    except ValueError as e:
        logger.warning(f"❌ Google token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_INVALID_GOOGLE_TOKEN
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected Google auth error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google auth error: {str(e)}"
        )

    try:
        # Check for existing user by google_id OR email
        user = db.query(User).filter(User.google_id == google_id).first()

        if not user:
            # User doesn't exist by google_id, check if they exist by email
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                # User exists with this email (from previous email/password registration)
                logger.info(f"Linking Google OAuth to existing user: {email}")
                # Update their google_id to link their Google account
                user.google_id = google_id
                user.profile_picture = picture or user.profile_picture
                user.verified = "True"  # Google OAuth counts as verified
                db.commit()
                db.refresh(user)
            else:
                # Completely new user, create from Google OAuth
                logger.info(f"Creating new user from Google OAuth: {email}")
                user = User(
                    email=email,
                    name=name or email.split("@")[0],  # Fallback name from email
                    google_id=google_id,
                    profile_picture=picture,
                    verified="True",  # Google has already verified the email
                    created_at=get_unix_timestamp()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"✅ New Google user created: {user.id}")
        else:
            logger.info(f"Existing Google user found: {user.id}")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        logger.info(f"✅ Tokens created for user: {user.id}")

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                profile_picture=user.profile_picture
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Google auth database error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google auth failed: {str(e)}"
        )
 
@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_USER_ALREADY_EXISTS
        )

    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        name=user_data.name,
        password=hashed_password,
        verified="False"  # User must verify email before accessing account
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create email verification token (valid for 24 hours)
    verification_token = str(uuid.uuid4())
    expires_at = get_unix_timestamp() + (24 * 60 * 60)  # 24 hours

    email_token = EmailVerificationToken(
        token=verification_token,
        user_id=user.id,
        email=user.email,
        expires_at=expires_at
    )
    db.add(email_token)
    db.commit()

    # Send verification email
    verification_link = f"{settings.FRONTEND_URL}/auth/verify-email/{verification_token}"
    send_email(user.email, verification_link, email_type="verification")

    return RegisterResponse(
        message="Registration successful. Please check your email to verify your account.",
        email=user.email
    )


@router.post("/verify-email", response_model=VerifyEmailResponse)
@limiter.limit("10/minute")
def verify_email(request: Request, verify_data: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify user's email using the verification token.
    """
    # Check if token exists and is valid
    token_record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == verify_data.token
    ).first()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    # Check if token has expired
    if get_unix_timestamp() > token_record.expires_at:
        db.delete(token_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please register again."
        )

    # Check if token was already used
    if token_record.verified_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    # Mark user as verified
    user = token_record.user
    if user:
        user.verified = "True"
        token_record.verified_at = get_unix_timestamp()
        db.commit()

    return VerifyEmailResponse(
        message="Email verified successfully. You can now log in."
    )


class ResendVerificationRequest(BaseModel):
    email: EmailStr


@router.post("/resend-verification", response_model=VerifyEmailResponse)
@limiter.limit("5/minute")
def resend_verification(request: Request, resend_data: ResendVerificationRequest, db: Session = Depends(get_db)):
    """
    Resend verification email to user if they didn't receive it.
    """
    user = db.query(User).filter(User.email == resend_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already verified
    if user.verified == "True":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Delete old verification tokens for this user
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id
    ).delete()
    db.commit()
    
    # Create new verification token (valid for 24 hours)
    verification_token = str(uuid.uuid4())
    expires_at = get_unix_timestamp() + (24 * 60 * 60)
    
    email_token = EmailVerificationToken(
        token=verification_token,
        user_id=user.id,
        email=user.email,
        expires_at=expires_at
    )
    db.add(email_token)
    db.commit()
    
    # Send verification email
    verification_link = f"{settings.FRONTEND_URL}/auth/verify-email/{verification_token}"
    try:
        send_email(user.email, verification_link, email_type="verification")
        return VerifyEmailResponse(
            message="Verification email sent. Check your inbox (and spam folder)."
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to send verification email. Please try again later."
        )

 
@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
def login(request: Request, login_data: UserLogin, db: Session = Depends(get_db)):
    logger = logging.getLogger(__name__)
    logger.info(f"Login attempt for email: {login_data.email}")
    
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user:
        logger.warning(f"User not found: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.password:
        logger.warning(f"User has no password: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not verify_password(login_data.password, user.password):
        logger.warning(f"Password verification failed for: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if email is verified
    is_verified = user.verified == "True" or user.verified == True
    if not is_verified:
        logger.warning(f"Email not verified for: {login_data.email} (verified={user.verified})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. Check your inbox for the verification link."
        )

    logger.info(f"Login successful for: {login_data.email}")
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            profile_picture=user.profile_picture
        )
    )


 
from pydantic import BaseModel
@router.post("/refresh", response_model=RefreshTokenResponse)
@limiter.limit("30/minute")
def refresh_token_endpoint(request: Request, refresh_token: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    Refresh access token using a valid refresh token.
    Issues new tokens and revokes the old refresh token (stored in blacklist).
    """     
    user_id = verify_refresh_token(refresh_token, db)
    delete_refresh_token(refresh_token, db)
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    return RefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(data: ForgotPasswordRequest,
                db:Session = Depends(get_db)):
    email = data.email
    user = db.query(User).filter(User.email==email).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            , detail="User not found")

    token = str(uuid.uuid4())
    expires_at = get_unix_timestamp() + (settings.PASSWORD_RESET_EXPIRE_MINUTES * 60)

    # Store token in database
    reset_token = PasswordResetToken(
        token=token,
        user_id=user.id,
        email=email,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()

    reset_link = f"{settings.FRONTEND_URL}/auth/reset-password/{token}"

    # Send verification email
    send_email(email, reset_link, email_type="password_reset")

    return ForgotPasswordResponse(message="Reset link sent to your email")


@router.post("/reset-password/{token}", response_model=ResetPasswordResponse)
def reset_password(token: str, data: ResetPasswordRequest, db: Session = Depends(get_db)):
    
    # Check token exists
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Check expiry
    if get_unix_timestamp() > reset_token.expires_at:
        db.delete(reset_token)
        db.commit()
        raise HTTPException(status_code=400, detail="Token expired")

    # Check if token already used
    if reset_token.used is not None:
        raise HTTPException(status_code=400, detail="Token already used")

    # Update password in database
    user = reset_token.user
    if user:
        user.password = hash_password(data.password)
        reset_token.used = get_unix_timestamp()
        db.commit()

    return ResetPasswordResponse(message="Password updated successfully")