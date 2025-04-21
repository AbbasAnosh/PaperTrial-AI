from supabase import create_client, Client
from app.core.config import settings
import logging

class StorageService:
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

    async def upload_file(self, file_path: str, storage_path: str) -> str:
        """Upload a file to Supabase Storage and return the URL"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Upload to Supabase Storage
            response = self.supabase.storage.from_('form-submissions').upload(
                storage_path,
                file_data
            )
            
            # Get public URL
            url = self.supabase.storage.from_('form-submissions').get_public_url(storage_path)
            return url
            
        except Exception as e:
            logging.error(f"Error uploading file to Supabase: {str(e)}", exc_info=True)
            raise

    async def download_file(self, storage_path: str, local_path: str):
        """Download a file from Supabase Storage"""
        try:
            # Download file data
            file_data = self.supabase.storage.from_('form-submissions').download(storage_path)
            
            # Save to local path
            with open(local_path, 'wb') as f:
                f.write(file_data)
                
        except Exception as e:
            logging.error(f"Error downloading file from Supabase: {str(e)}", exc_info=True)
            raise

    async def delete_file(self, storage_path: str):
        """Delete a file from Supabase Storage"""
        try:
            self.supabase.storage.from_('form-submissions').remove([storage_path])
        except Exception as e:
            logging.error(f"Error deleting file from Supabase: {str(e)}", exc_info=True)
            raise 