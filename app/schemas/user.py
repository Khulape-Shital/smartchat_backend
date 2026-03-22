from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional
from uuid import UUID

class UserBase(BaseModel):
    email:EmailStr
    name: str

class UserCreate(BaseModel):
    email : EmailStr
    name :str
 
    password: str = Field(min_length=8, max_length=72)

class UserLogin(BaseModel):
    email :EmailStr
    password:str

class GoogleAuth(BaseModel):
    token:str
 
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email:EmailStr
    name:str
    profile_picture :Optional[str]=None

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=72)


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordResponse(BaseModel):
    message: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    message: str


class RegisterResponse(BaseModel):
    message: str
    email: str