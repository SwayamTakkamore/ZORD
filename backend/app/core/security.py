"""Security utilities for password hashing and JWT token management"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
import jwt
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration from environment variables
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_MINUTES = int(os.getenv("JWT_EXP_MINUTES", "30"))

# Validate JWT configuration
if JWT_SECRET == "dev-secret-change-in-production":
    logger.warning("Using default JWT_SECRET! Set JWT_SECRET environment variable in production")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hashed password
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    sub: str, 
    data: Optional[Dict[str, Any]] = None, 
    expires_minutes: Optional[int] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        sub: Subject (usually user ID)
        data: Additional data to include in token
        expires_minutes: Token expiration time in minutes
        
    Returns:
        str: Encoded JWT token
    """
    if expires_minutes is None:
        expires_minutes = JWT_EXP_MINUTES
    
    # Create payload
    payload = {
        "sub": sub,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    # Add additional data if provided
    if data:
        payload.update(data)
    
    try:
        # Encode token
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug(f"Created access token for subject: {sub}")
        return token
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT access token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Dict[str, Any]: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode and verify token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Validate subject
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject"
            )
        
        logger.debug(f"Verified access token for subject: {sub}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Access token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )


def get_token_subject(token: str) -> str:
    """
    Extract subject from token without full verification
    
    Args:
        token: JWT token
        
    Returns:
        str: Token subject (user ID)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if token is expired without raising exceptions
    
    Args:
        token: JWT token to check
        
    Returns:
        bool: True if expired, False if valid
    """
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return False
    except jwt.ExpiredSignatureError:
        return True
    except Exception:
        return True  # Treat any other error as expired