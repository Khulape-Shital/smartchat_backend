from pydantic import BaseModel, ConfigDict, field_validator
 
from typing import Optional, Literal
from uuid import UUID
from app.core.constants import DEFAULT_CHAT_TITLE
from app.core.time_utils import get_unix_timestamp

class ChatSessionCreate(BaseModel):
    title: Optional[str] = DEFAULT_CHAT_TITLE

class ChatSessionUpdate(BaseModel):
    title: str

class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: Optional[str] = DEFAULT_CHAT_TITLE
    created_at: int
    updated_at: int

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def convert_timestamp_to_int(cls, v):
        if v is None:
            return get_unix_timestamp()
        return int(v) if isinstance(v, (int, float, str)) else v

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
    
    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def convert_timestamp_to_int(cls, v):
        if v is None:
            return get_unix_timestamp()
        return int(v) if isinstance(v, (int, float, str)) else v
    
    @field_validator("file", mode="before")
    @classmethod
    def transform_file_path(cls, v):
        if v and not v.startswith("http"):
            return f"/media/{v}"
        return v

