from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class MovieCreate(BaseModel):
    title: str
    description: str
    director: str
    year: int
    rating: float

class MovieUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    director: Optional[str] = None
    year: Optional[int] = None
    rating: Optional[float] = None

class MovieOut(BaseModel):
    id: int
    title: str
    description: str
    director: str
    year: int
    rating: float

    class Config:
        from_attributes = True

class MoviesResponse(BaseModel):
    movies: list[MovieOut]
    total: int
    page: int
    total_pages: int

class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)

class UserLoginRequest(BaseModel):
    username: str
    password: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str

class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    expires_in: int

class ChatMessageOut(BaseModel):
    sender: str
    recipient: Optional[str] = None
    text: str
    created_at: datetime

class RoomHistoryResponse(BaseModel):
    room: str
    messages: list[ChatMessageOut]
