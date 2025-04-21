"""
User service for managing user-related operations.
"""

from typing import Optional, List
from datetime import datetime
import logging
import bcrypt
from supabase import Client, create_client

from app.core.config import settings
from app.models.user import UserCreate, UserInDB, UserResponse, User, UserUpdate

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            response = self.supabase.table("users").select("*").eq("id", user_id).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            raise

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            response = self.supabase.table("users").select("*").eq("email", email).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            raise

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(
            plain_password.encode(),
            hashed_password.encode()
        )

    async def create(self, user: UserCreate) -> User:
        """Create a new user."""
        try:
            # Check if email already exists
            existing_user = await self.get_by_email(user.email)
            if existing_user:
                raise ValueError("Email already registered")

            # Hash password
            hashed_password = self._hash_password(user.password)

            # Create user document
            user_dict = user.dict()
            user_dict.pop("password")
            user_dict.update({
                "password": hashed_password,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })

            # Insert into database
            response = self.supabase.table("users").insert(user_dict).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            raise ValueError("Failed to create user")
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    async def update(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """Update user information."""
        try:
            update_data = user_update.dict(exclude_unset=True)
            
            if "password" in update_data:
                update_data["password"] = self._hash_password(update_data["password"])
            
            update_data["updated_at"] = datetime.utcnow().isoformat()

            response = self.supabase.table("users").update(update_data).eq("id", user_id).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise

    async def delete(self, user_id: str) -> bool:
        """Delete a user."""
        try:
            response = self.supabase.table("users").delete().eq("id", user_id).execute()
            return response.data and len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise

    async def list_users(self, skip: int = 0, limit: int = 10) -> List[User]:
        """List users with pagination."""
        try:
            response = self.supabase.table("users").select("*").range(skip, skip + limit - 1).execute()
            if response.data:
                return [User(**user_data) for user_data in response.data]
            return []
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            raise 