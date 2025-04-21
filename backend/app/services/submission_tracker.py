from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
from app.database import get_db

class SubmissionTracker:
    def __init__(self):
        self.db = get_db()

    async def create_submission(self, user_id: str, form_id: str, form_data: Dict[str, Any]) -> str:
        """Create a new form submission record"""
        submission_id = str(uuid.uuid4())
        
        submission_data = {
            "id": submission_id,
            "user_id": user_id,
            "form_id": form_id,
            "form_data": form_data,
            "status": "queued",
            "events": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = await self.db.table('submissions').insert(submission_data).execute()
        if not response.data:
            raise Exception("Failed to create submission record")
        
        return submission_id

    async def update_submission_status(self, submission_id: str, status: str, message: str) -> Dict[str, Any]:
        """Update the status of a submission"""
        update_data = {
            "status": status,
            "message": message,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = await self.db.table('submissions').update(update_data).eq('id', submission_id).execute()
        if not response.data:
            raise Exception("Failed to update submission status")
        
        return response.data[0]

    async def add_submission_event(self, submission_id: str, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add an event to the submission history"""
        event = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get current submission
        response = await self.db.table('submissions').select('*').eq('id', submission_id).single().execute()
        if not response.data:
            raise Exception("Submission not found")
        
        submission = response.data
        events = submission.get('events', [])
        events.append(event)
        
        # Update submission with new event
        update_data = {
            "events": events,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = await self.db.table('submissions').update(update_data).eq('id', submission_id).execute()
        if not response.data:
            raise Exception("Failed to add submission event")
        
        return response.data[0]

    async def get_submission(self, submission_id: str, user_id: str) -> Dict[str, Any]:
        """Get a submission by ID"""
        response = await self.db.table('submissions').select('*').eq('id', submission_id).eq('user_id', user_id).single().execute()
        if not response.data:
            raise Exception("Submission not found")
        
        return response.data

    async def get_user_submissions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all submissions for a user"""
        response = await self.db.table('submissions').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return response.data

    async def get_submission_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get submission history with events"""
        submissions = await self.get_user_submissions(user_id)
        
        return [
            {
                "id": sub["id"],
                "form_id": sub["form_id"],
                "status": sub["status"],
                "message": sub.get("message"),
                "created_at": sub["created_at"],
                "updated_at": sub["updated_at"],
                "events": sub.get("events", [])
            }
            for sub in submissions
        ] 