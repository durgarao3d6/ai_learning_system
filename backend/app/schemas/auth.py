"""Authentication and user schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password with minimum 8 characters")


class LoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token authentication response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Schema for access token refresh request."""

    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: str
    created_at: datetime
