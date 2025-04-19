from typing import Dict, List, Any
from datetime import datetime
from app.core.supabase_client import SupabaseClient
from app.services.ai_service import AIService

class SubmissionTracker:
    def __init__(self):
        self.supabase = SupabaseClient()
        self.ai_service = AIService()

    async def create_submission(self, user_id: str, form_data: Dict[str, Any]) -> str:
        """Create a new submission record with detailed initial state"""
        submission = {
            "user_id": user_id,
            "form_data": form_data,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "timeline": [{
                "event": "created",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "form_type": form_data.get("form_type", "unknown"),
                    "field_count": len(form_data.get("fields", {})),
                    "source": form_data.get("source", "manual")
                }
            }],
            "history": {
                "status_changes": [],
                "field_updates": [],
                "ai_interactions": []
            }
        }
        
        result = await self.supabase.table("submissions").insert(submission).execute()
        return result.data[0]["id"]

    async def update_submission_status(self, submission_id: str, status: str, details: Dict[str, Any] = None):
        """Update submission status and add detailed timeline entry"""
        submission = await self.supabase.table("submissions").select("*").eq("id", submission_id).single().execute()
        
        if not submission.data:
            raise ValueError("Submission not found")
        
        timeline = submission.data["timeline"]
        history = submission.data["history"]
        
        # Add status change to history
        history["status_changes"].append({
            "from": submission.data["status"],
            "to": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        })
        
        # Add timeline event
        timeline.append({
            "event": "status_update",
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        })
        
        await self.supabase.table("submissions").update({
            "status": status,
            "timeline": timeline,
            "history": history,
            "updated_at": datetime.now().isoformat()
        }).eq("id", submission_id).execute()

    async def add_submission_event(self, submission_id: str, event: str, details: Dict[str, Any]):
        """Add a detailed event to the submission timeline"""
        submission = await self.supabase.table("submissions").select("*").eq("id", submission_id).single().execute()
        
        if not submission.data:
            raise ValueError("Submission not found")
        
        timeline = submission.data["timeline"]
        history = submission.data["history"]
        
        # Add to appropriate history section
        if event == "field_update":
            history["field_updates"].append({
                "timestamp": datetime.now().isoformat(),
                "details": details
            })
        elif event.startswith("ai_"):
            history["ai_interactions"].append({
                "timestamp": datetime.now().isoformat(),
                "details": details
            })
        
        # Add timeline event
        timeline.append({
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "details": details
        })
        
        await self.supabase.table("submissions").update({
            "timeline": timeline,
            "history": history,
            "updated_at": datetime.now().isoformat()
        }).eq("id", submission_id).execute()

    async def get_submission_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get detailed submission history for a user"""
        result = await self.supabase.table("submissions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        # Add AI analysis to each submission
        for submission in result.data:
            if submission["status"] == "completed":
                analysis = await self.ai_service.analyze_form_fields(submission["form_data"])
                submission["ai_analysis"] = analysis
        
        return result.data

    async def get_submission_timeline(self, submission_id: str) -> Dict[str, Any]:
        """Get comprehensive timeline and history for a submission"""
        submission = await self.supabase.table("submissions").select("*").eq("id", submission_id).single().execute()
        
        if not submission.data:
            raise ValueError("Submission not found")
        
        # Generate summary statistics
        timeline = submission.data["timeline"]
        history = submission.data["history"]
        
        stats = {
            "total_events": len(timeline),
            "status_changes": len(history["status_changes"]),
            "field_updates": len(history["field_updates"]),
            "ai_interactions": len(history["ai_interactions"]),
            "duration": self._calculate_duration(timeline)
        }
        
        return {
            "timeline": timeline,
            "history": history,
            "stats": stats
        }

    def _calculate_duration(self, timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate duration between first and last event"""
        if not timeline:
            return {"total": 0, "unit": "seconds"}
        
        start_time = datetime.fromisoformat(timeline[0]["timestamp"])
        end_time = datetime.fromisoformat(timeline[-1]["timestamp"])
        duration = (end_time - start_time).total_seconds()
        
        return {
            "total": duration,
            "unit": "seconds"
        } 