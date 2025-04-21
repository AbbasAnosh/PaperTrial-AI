"""
Authentication service for handling JWT tokens and authentication.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from supabase import Client, create_client

from app.core.config import settings
from app.models.user import User, UserCreate
from app.core.exceptions import AuthenticationError, NotFoundException
from app.services.user_service import UserService
from app.models.auth import UserResponse, TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, supabase_client: Client, user_service: UserService):
        """Initialize the auth service with Supabase client and user service."""
        self.supabase = supabase_client
        self.user_service = user_service

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return pwd_context.hash(password)

    async def authenticate_user(self, email: str, password: str) -> UserResponse:
        """Authenticate a user and return user object if successful."""
        try:
            user = await self.user_service.get_by_email(email)
            if not user:
                return None
            
            if not self.verify_password(password, user.hashed_password):
                return None
            
            return user
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error during authentication"
            )

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user in Supabase."""
        # Check if user already exists
        existing_user = await self.user_service.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = self.get_password_hash(user_data.password)
        user_dict = user_data.model_dump()
        user_dict["hashed_password"] = hashed_password
        del user_dict["password"]
        
        return await self.user_service.create(user_dict)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT access token."""
        try:
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(
                to_encode,
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )

    async def get_current_user(self, token: str) -> UserResponse:
        """Get the current user from a JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            
            user = await self.user_service.get_by_id(user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            return user
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving user information"
            )

    async def get_current_active_user(self, token: str) -> UserResponse:
        """Get the current active user from a JWT token."""
        user = await self.get_current_user(token)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        return user

    async def authenticate_and_create_token(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate a user and create an access token."""
        user = await self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token = self.create_access_token(user)
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        } 