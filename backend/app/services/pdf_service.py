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

    async def process_pdf(self, file_data: bytes, filename: str, form_type: str, user_email: str) -> Dict:
        """Process a PDF file and store it in Supabase storage"""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            file_path = f"documents/{user_email}/{file_id}/{filename}"
            
            # Upload file to Supabase storage
            await self.storage.from_('documents').upload(file_path, file_data)
            
            # Create document record
            document = DocumentCreate(
                filename=filename,
                form_type=form_type,
                user_email=user_email
            )
            
            # Insert document into database
            response = await self.db.table('documents').insert({
                **document.dict(),
                'file_path': file_path,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).execute()
            
            if not response.data:
                raise Exception("Failed to create document record")
            
            return response.data[0]
            
        except Exception as e:
            # Clean up storage if database insert fails
            if 'file_path' in locals():
                await self.storage.from_('documents').remove([file_path])
            raise e

    async def get_pdf_url(self, document_id: str, user_email: str) -> Optional[str]:
        """Get a signed URL for a PDF file"""
        try:
            # Get document record
            response = await self.db.table('documents').select('file_path').eq('id', document_id).eq('user_email', user_email).single()
            if not response.data:
                return None
            
            # Generate signed URL
            file_path = response.data['file_path']
            url = await self.storage.from_('documents').create_signed_url(file_path, 3600)  # 1 hour expiry
            
            return url['signedURL']
        except Exception:
            return None

    async def update_document_status(self, document_id: str, user_email: str, status: str, extracted_fields: Optional[Dict] = None) -> Dict:
        """Update document status and extracted fields"""
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if extracted_fields is not None:
            update_data['extracted_fields'] = extracted_fields
        
        response = await self.db.table('documents').update(update_data).eq('id', document_id).eq('user_email', user_email)
        if not response.data:
            raise Exception("Failed to update document")
        
        return response.data[0] 