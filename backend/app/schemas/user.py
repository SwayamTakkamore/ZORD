"""Pydantic schemas for user authentication requests and responses"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional


class UserSignupRequest(BaseModel):
    """
    Schema for user signup request
    
    Example:
    {
        "username": "swayam",
        "email": "swayam@example.com", 
        "password": "StrongPassw0rd!"
    }
    """
    username: str = Field(..., min_length=3, max_length=32, description="Unique username")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """Basic password validation"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserLoginRequest(BaseModel):
    """
    Schema for user login request
    
    Example:
    {
        "email": "swayam@example.com",
        "password": "StrongPassw0rd!"
    }
    """
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """
    Schema for user response (with token)
    
    Example:
    {
        "id": "653f1a2e....",
        "username": "swayam",
        "email": "swayam@example.com",
        "role": "user",
        "token": "eyJhbGciOiJIU..."
    }
    """
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role")
    token: str = Field(..., description="JWT access token")


class UserProfileResponse(BaseModel):
    """
    Schema for user profile response (without token)
    
    Example:
    {
        "id": "653f1a2e....",
        "username": "swayam",
        "email": "swayam@example.com",
        "role": "user"
    }
    """
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role")
    created_at: Optional[str] = Field(None, description="Account creation date")
    last_login: Optional[str] = Field(None, description="Last login date")


class ErrorResponse(BaseModel):
    """
    Schema for error responses
    
    Example:
    {
        "error": "validation_error",
        "detail": "Email already registered"
    }
    """
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")