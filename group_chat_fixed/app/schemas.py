from pydantic import BaseModel
from typing import List, Optional
import datetime

class GroupBase(BaseModel):
    name: str
    description: str
    tags: str

class GroupCreate(GroupBase):
    pass

class GroupResponse(GroupBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    group_id: int
    user_id: int

class MessageResponse(MessageBase):
    id: int
    group_id: int
    user_id: int
    timestamp: datetime.datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
