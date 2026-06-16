from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    
class ChatCreateRequest(BaseModel):
    title: str = "New chat"


class ChatOut(BaseModel):
    id: int
    user_id: int
    title: str


class MessageCreateRequest(BaseModel):
    role: str
    content: str


class MessageOut(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str