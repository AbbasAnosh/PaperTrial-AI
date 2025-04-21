from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.supabase_client import SupabaseClient
from app.services.ai_service import AIService
import os
import uuid
from app.database import get_db
from app.models.user import UserInDB
from app.models.document import DocumentInDB
from app.models.user_profile import UserProfileCreate, UserProfileUpdate, UserProfileInDB

class UserProfileService:
    def __init__(self):
        self.supabase = SupabaseClient()
        self.ai_service = AIService()
        self.upload_dir = "uploads"
        self.db = get_db()

    async def get_profile(self, user_id: str) -> Optional[UserProfileInDB]:
        """Get user profile by user ID"""
        response = await self.db.table('user_profiles').select('*').eq('user_id', user_id).single().execute()
        return response.data

    async def update_profile(self, user_id: str, profile_data: UserProfileUpdate) -> UserProfileInDB:
        """Update user profile"""
        update_data = {
            **profile_data.dict(exclude_unset=True),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Check if profile exists
        existing = await self.get_profile(user_id)
        if not existing:
            # Create new profile
            create_data = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                **update_data
            }
            response = await self.db.table('user_profiles').insert(create_data).execute()
        else:
            # Update existing profile
            response = await self.db.table('user_profiles').update(update_data).eq('user_id', user_id).execute()

        return response.data[0]

    async def upload_document(self, user_id: str, file_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload and store a document"""
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_extension = metadata.get("extension", "pdf")
            filename = f"{file_id}.{file_extension}"
            
            # Save file
            os.makedirs(self.upload_dir, exist_ok=True)
            file_path = os.path.join(self.upload_dir, filename)
            with open(file_path, "wb") as f:
                f.write(file_data)
            
            # Store metadata
            document = {
                "user_id": user_id,
                "file_id": file_id,
                "filename": filename,
                "file_path": file_path,
                "document_type": metadata.get("type"),
                "uploaded_at": datetime.now().isoformat(),
                "metadata": metadata
            }
            
            result = await self.supabase.table("documents").insert(document).execute()
            return result.data[0]
        except Exception as e:
            raise Exception(f"Failed to upload document: {str(e)}")

    async def get_document(self, user_id: str, document_id: str) -> Dict[str, Any]:
        """Get document metadata and content"""
        try:
            result = await self.supabase.table("documents").select("*").eq("user_id", user_id).eq("file_id", document_id).single().execute()
            if not result.data:
                raise ValueError("Document not found")
            
            # Read file content
            with open(result.data["file_path"], "rb") as f:
                content = f.read()
            
            return {
                "metadata": result.data,
                "content": content
            }
        except Exception as e:
            raise Exception(f"Failed to get document: {str(e)}")

    async def _validate_profile_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate profile data using AI"""
        prompt = f"""
        Validate this profile data:
        {data}
        
        Check for:
        - Required fields
        - Format validation (email, phone, etc.)
        - Consistency with previous data
        - Potential errors or inconsistencies
        
        Return a JSON object with:
        - is_valid: boolean
        - errors: list of validation errors
        - suggestions: list of improvements
        """
        
        response = await self.ai_service.analyze_form_fields([{"content": prompt}])
        return response

    def _create_default_profile(self, user_id: str) -> Dict[str, Any]:
        """Create a default profile for new users"""
        return {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "documents": [],
            "form_history": [],
            "profile_data": {
                "personal_info": {},
                "contact_info": {},
                "identification": {},
                "addresses": [],
                "preferences": {}
            }
        }

    async def get_user_profile(self, email: str) -> Dict:
        """Get user profile information"""
        response = await self.db.table('users').select('*').eq('email', email).single()
        if not response.data:
            raise Exception("User not found")
        
        user = response.data
        return {
            "email": user["email"],
            "name": user.get("name"),
            "company": user.get("company"),
            "preferences": user.get("preferences", {})
        }

    async def update_user_profile(self, email: str, profile_data: Dict) -> Dict:
        """Update user profile information"""
        update_data = {
            "name": profile_data.get("name"),
            "company": profile_data.get("company"),
            "preferences": profile_data.get("preferences", {}),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = await self.db.table('users').update(update_data).eq('email', email)
        if not response.data:
            raise Exception("Failed to update user profile")
        
        return await self.get_user_profile(email)

    async def get_user_documents(self, user_id: str) -> List[dict]:
        """Get all documents for a user"""
        response = await self.db.table('documents').select('*').eq('user_id', user_id).execute()
        return response.data

    async def delete_document(self, user_id: str, document_id: str) -> None:
        """Delete a document"""
        # First get the document to verify ownership
        doc = await self.db.table('documents').select('*').eq('id', document_id).eq('user_id', user_id).single().execute()
        if not doc.data:
            raise Exception("Document not found or access denied")

        # Delete from storage
        await self.db.storage.from_('documents').remove([doc.data['file_path']])

        # Delete from database
        await self.db.table('documents').delete().eq('id', document_id).execute() 