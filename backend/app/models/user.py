"""User model for MongoDB with Pydantic validation"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from bson import ObjectId


class UserModel(BaseModel):
    """
    User model for MongoDB storage
    
    Fields:
    - id: MongoDB ObjectId (auto-generated)
    - username: Unique username (3-32 chars)
    - email: Unique email address
    - password_hash: bcrypt hashed password
    - role: user role (user/admin)
    - created_at: Account creation timestamp
    - last_login: Last login timestamp (optional)
    - disabled: Account status flag
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )
    
    id: Optional[ObjectId] = Field(default=None, alias="_id")
    username: str = Field(..., min_length=3, max_length=32, description="Unique username")
    email: EmailStr = Field(..., description="Unique email address")
    password_hash: str = Field(..., description="bcrypt hashed password")
    role: str = Field(default="user", description="User role (user/admin)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    disabled: bool = Field(default=False, description="Account disabled flag")
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserModel":
        """Create UserModel from MongoDB document"""
        if "_id" in data:
            data["id"] = data["_id"]
        return cls(**data)
    
    def to_dict(self) -> dict:
        """Convert UserModel to MongoDB document format"""
        data = self.model_dump(by_alias=True, exclude_unset=True)
        if "id" in data:
            data["_id"] = data.pop("id")
        return data
    
    def to_response_dict(self) -> dict:
        """Convert to response format (without sensitive data)"""
        return {
            "id": str(self.id) if self.id else None,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "disabled": self.disabled
        }