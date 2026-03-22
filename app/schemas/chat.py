from pydantic import BaseModel, ConfigDict, field_validator
 
from typing import Optional, Literal
from uuid import UUID
from app.core .constants import DEFAULT_CHAT_TITLE

class ChatSessionCreate(BaseModel):
    title: Optional[str] = DEFAULT_CHAT_TITLE

class ChatSessionUpdate(BaseModel):
    title: str

class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    created_at: int
    updated_at: int

class MessageCreate(BaseModel):
    message:Optional[str]=None

class EditMessage(BaseModel):
    message :str

class MessageFeedback(BaseModel):
    feedback: Optional[Literal["like", "dislike"]] = None

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    role:str
    status: int = 200
    message: str = "Success"
    ai_response:Optional[str]=None
    feedback: Optional[str] = None
    file: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    created_at: int
    updated_at: int
    
    @field_validator("file", mode="before")
    @classmethod
    def transform_file_path(cls, v):
        if v and not v.startswith("http"):
            return f"/media/{v}"
        return v

