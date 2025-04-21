from typing import Dict, Optional
import os
import uuid
from datetime import datetime
from app.database import get_db
from app.models.document import DocumentCreate, DocumentInDB

class PDFService:
    def __init__(self):
        self.db = get_db()
        self.storage = self.db.storage

    async def process_pdf(self, file_data: bytes, filename: str, form_type: str, user_id: str) -> Dict:
        """Process a PDF file and store it in Supabase storage"""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            file_path = f"documents/{user_id}/{file_id}/{filename}"
            
            # Upload file to Supabase storage
            self.storage.from_('documents').upload(file_path, file_data)
            
            # Create document record with actual table fields
            document_data = {
                'file_name': filename,
                'file_type': form_type,
                'file_path': file_path,
                'original_name': filename,  # Store original filename
                'size': len(file_data),  # Store file size in bytes
                'user_id': user_id,  # Use the provided UUID
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Try to insert with actual fields
            response = self.db.table('documents').insert(document_data).execute()
            
            if not response.data:
                raise Exception("Failed to create document record")
            
            return response.data[0]
            
        except Exception as e:
            # Clean up storage if database insert fails
            if 'file_path' in locals():
                self.storage.from_('documents').remove([file_path])
            raise e

    async def get_pdf_url(self, document_id: str, user_id: str) -> Optional[str]:
        """Get a signed URL for a PDF file"""
        try:
            # Get document record
            response = self.db.table('documents').select('file_path').eq('id', document_id).eq('user_id', user_id).single().execute()
            if not response.data:
                return None
            
            # Generate signed URL
            file_path = response.data['file_path']
            url = self.storage.from_('documents').create_signed_url(file_path, 3600)  # 1 hour expiry
            
            return url['signedURL']
        except Exception:
            return None

    async def update_document_status(self, document_id: str, user_id: str, extracted_fields: Optional[Dict] = None) -> Dict:
        """Update document with extracted fields"""
        try:
            update_data = {
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Only include extracted_fields if the column exists
            if extracted_fields is not None:
                try:
                    # Check if the column exists by trying to select it
                    self.db.table('documents').select('extracted_fields').limit(1).execute()
                    update_data['extracted_fields'] = extracted_fields
                except Exception:
                    # Column doesn't exist, skip it
                    pass
            
            response = self.db.table('documents').update(update_data).eq('id', document_id).eq('user_id', user_id).execute()
            if not response.data:
                raise Exception("Failed to update document")
            
            return response.data[0]
        except Exception as e:
            raise e 