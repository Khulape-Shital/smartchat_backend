"""API router configuration."""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat

 

api_router = APIRouter()
 
api_router.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
api_router.include_router(chat.router, prefix="/v1/chat", tags=["Chat"]) 