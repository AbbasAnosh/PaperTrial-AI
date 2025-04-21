"""
Security module for handling authentication and authorization.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def validate_password_strength(password: str) -> bool:
    """
    Validate password strength according to settings.
    Returns True if password meets all requirements.
    """
    # During development, only require minimum length
    if settings.ENVIRONMENT == "development":
        return len(password) >= 6
    
    # In production, enforce all requirements
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False
    
    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False
    
    if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False
    
    if settings.PASSWORD_REQUIRE_NUMBERS and not re.search(r'\d', password):
        return False
    
    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    Raises HTTPException if token is invalid.
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise credentials_exception

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get the current user from the token.
    This is a dependency that can be used in route handlers.
    """
    payload = verify_token(token)
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return {"user_id": user_id, "token_data": payload}

def check_permissions(required_permissions: list) -> bool:
    """
    Check if the current user has the required permissions.
    This is a placeholder - implement your permission logic here.
    """
    # TODO: Implement permission checking logic
    return True

def rate_limit_check(user_id: str) -> bool:
    """
    Check if the user has exceeded rate limits.
    This is a placeholder - implement your rate limiting logic here.
    """
    # TODO: Implement rate limiting logic using Redis
    return True

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.PyJWTError:
        return None 