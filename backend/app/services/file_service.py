from datetime import datetime, timedelta
from typing import List, Optional
from app.models.file_metadata import FileMetadata, FileMetadataCreate, FileMetadataUpdate
from app.core.supabase import supabase_client
from app.core.errors import NotFoundError, ValidationError

class FileService:
    """Service for managing file metadata and organization"""
    
    def __init__(self):
        self.table = "file_metadata"
    
    async def create_file_metadata(
        self,
        user_id: str,
        metadata: FileMetadataCreate
    ) -> FileMetadata:
        """Create new file metadata entry"""
        try:
            file_metadata = FileMetadata(
                user_id=user_id,
                **metadata.dict()
            )
            
            result = await supabase_client.table(self.table).insert(
                file_metadata.dict()
            ).execute()
            
            return FileMetadata(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error creating file metadata: {str(e)}")
    
    async def get_file_metadata(self, file_id: str, user_id: str) -> FileMetadata:
        """Get file metadata by ID"""
        try:
            result = await supabase_client.table(self.table)\
                .select("*")\
                .eq("id", file_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if not result.data:
                raise NotFoundError(f"File metadata {file_id} not found")
            
            return FileMetadata(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error getting file metadata: {str(e)}")
    
    async def get_user_files(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_inactive: bool = False
    ) -> List[FileMetadata]:
        """Get files for a user with optional filtering"""
        try:
            query = supabase_client.table(self.table)\
                .select("*")\
                .eq("user_id", user_id)
            
            if project_id:
                query = query.eq("project_id", project_id)
            if session_id:
                query = query.eq("session_id", session_id)
            if tags:
                query = query.contains("tags", tags)
            if not include_inactive:
                query = query.eq("is_active", True)
            
            result = await query.execute()
            return [FileMetadata(**file) for file in result.data]
        except Exception as e:
            raise ValidationError(f"Error getting user files: {str(e)}")
    
    async def update_file_metadata(
        self,
        file_id: str,
        user_id: str,
        update_data: FileMetadataUpdate
    ) -> FileMetadata:
        """Update file metadata"""
        try:
            # Get current metadata
            current = await self.get_file_metadata(file_id, user_id)
            
            # Update fields
            update_dict = update_data.dict(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await supabase_client.table(self.table)\
                .update(update_dict)\
                .eq("id", file_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return FileMetadata(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error updating file metadata: {str(e)}")
    
    async def create_new_version(
        self,
        file_id: str,
        user_id: str,
        new_file_path: str
    ) -> FileMetadata:
        """Create a new version of a file"""
        try:
            # Get current metadata
            current = await self.get_file_metadata(file_id, user_id)
            
            # Create new version
            new_metadata = FileMetadataCreate(
                file_name=current.file_name,
                file_path=new_file_path,
                file_type=current.file_type,
                file_size=current.file_size,
                mime_type=current.mime_type,
                project_id=current.project_id,
                session_id=current.session_id,
                tags=current.tags,
                expires_at=current.expires_at
            )
            
            # Create new version with incremented version number
            new_file = await self.create_file_metadata(user_id, new_metadata)
            
            # Update parent version reference
            await self.update_file_metadata(
                new_file.id,
                user_id,
                FileMetadataUpdate(parent_version_id=file_id)
            )
            
            return new_file
        except Exception as e:
            raise ValidationError(f"Error creating new version: {str(e)}")
    
    async def cleanup_expired_files(self) -> List[str]:
        """Clean up expired files and return list of cleaned file IDs"""
        try:
            now = datetime.utcnow()
            
            # Get expired files
            result = await supabase_client.table(self.table)\
                .select("id")\
                .lt("expires_at", now)\
                .eq("is_active", True)\
                .execute()
            
            expired_ids = [file["id"] for file in result.data]
            
            if expired_ids:
                # Mark files as inactive
                await supabase_client.table(self.table)\
                    .update({"is_active": False})\
                    .in_("id", expired_ids)\
                    .execute()
            
            return expired_ids
        except Exception as e:
            raise ValidationError(f"Error cleaning up expired files: {str(e)}")
    
    async def update_last_accessed(self, file_id: str, user_id: str) -> None:
        """Update last accessed timestamp for a file"""
        try:
            await supabase_client.table(self.table)\
                .update({"last_accessed": datetime.utcnow()})\
                .eq("id", file_id)\
                .eq("user_id", user_id)\
                .execute()
        except Exception as e:
            raise ValidationError(f"Error updating last accessed: {str(e)}") 