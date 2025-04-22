import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from ..models.admin import (
    SubmissionDetails,
    SystemMetrics,
    AdminAction,
    SubmissionList,
    AdminActionList,
    PaginatedResponse,
    AdminActionCreate
)
from ..models.form_submission import FormSubmission
from ..models.form_template import FormTemplate
from ..database import get_db
from ..tasks.form_processing import process_form_submission, retry_failed_submissions
from ..models.admin_action import AdminAction as AdminActionModel

logger = logging.getLogger(__name__)

class AdminService:
    """Service for admin operations and manual overrides"""
    
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def is_admin(self, user_id: UUID) -> bool:
        """Check if a user has admin privileges."""
        query = """
            SELECT is_admin 
            FROM users 
            WHERE id = :user_id
        """
        result = await self.db.fetch_one(query, {"user_id": user_id})
        return result and result["is_admin"]

    async def get_submission_details(self, submission_id: UUID) -> Optional[SubmissionDetails]:
        """Get detailed information about a specific submission."""
        query = """
            SELECT 
                s.*,
                ft.name as template_name,
                u.email as user_email
            FROM form_submissions s
            JOIN form_templates ft ON s.template_id = ft.id
            JOIN users u ON s.user_id = u.id
            WHERE s.id = :submission_id
        """
        submission = await self.db.fetch_one(query, {"submission_id": submission_id})
        
        if not submission:
            return None
            
        return SubmissionDetails(
            id=submission["id"],
            template_id=submission["template_id"],
            template_name=submission["template_name"],
            user_id=submission["user_id"],
            user_email=submission["user_email"],
            status=submission["status"],
            data=submission["data"],
            created_at=submission["created_at"],
            updated_at=submission["updated_at"],
            error_category=submission["error_category"],
            error_code=submission["error_code"],
            error_details=submission["error_details"],
            processing_started_at=submission["processing_started_at"],
            processing_completed_at=submission["processing_completed_at"],
            processing_duration_ms=submission["processing_duration_ms"],
            retry_count=submission["retry_count"],
            max_retries=submission["max_retries"],
            next_retry_at=submission["next_retry_at"]
        )

    async def retry_submission(self, submission_id: UUID) -> bool:
        """Retry a failed submission."""
        # Get submission details
        submission = await self.get_submission_details(submission_id)
        if not submission or submission.status != "failed":
            return False
            
        # Check if max retries exceeded
        if submission.retry_count >= submission.max_retries:
            return False
            
        # Queue the retry task
        process_form_submission.delay(
            str(submission_id),
            str(submission.template_id),
            submission.data,
            str(submission.user_id)
        )
        
        # Log the retry action
        await self._log_admin_action(
            AdminActionCreate(
                admin_id=submission.user_id,  # Using the original user as admin for now
                action="retry_submission",
                entity_type="submission",
                entity_id=submission_id,
                details={"retry_count": submission.retry_count + 1}
            )
        )
        
        return True

    async def force_delete_submission(self, submission_id: UUID) -> bool:
        """Force delete a submission."""
        # Check if submission exists
        submission = await self.get_submission_details(submission_id)
        if not submission:
            return False
            
        # Delete the submission
        query = "DELETE FROM form_submissions WHERE id = :submission_id"
        await self.db.execute(query, {"submission_id": submission_id})
        
        # Log the deletion action
        await self._log_admin_action(
            AdminActionCreate(
                admin_id=submission.user_id,  # Using the original user as admin for now
                action="delete_submission",
                entity_type="submission",
                entity_id=submission_id,
                details={"status": submission.status}
            )
        )
        
        return True

    async def get_submission_logs(self, submission_id: UUID) -> Optional[List[Dict[str, Any]]]:
        """Get logs for a specific submission."""
        # Check if submission exists
        submission = await self.get_submission_details(submission_id)
        if not submission:
            return None
            
        # Get logs from the database
        query = """
            SELECT 
                l.*,
                u.email as user_email
            FROM submission_logs l
            JOIN users u ON l.user_id = u.id
            WHERE l.submission_id = :submission_id
            ORDER BY l.created_at DESC
        """
        logs = await self.db.fetch_all(query, {"submission_id": submission_id})
        
        return [dict(log) for log in logs]

    async def get_all_submissions(
        self,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[UUID] = None,
        template_id: Optional[UUID] = None
    ) -> PaginatedResponse[SubmissionDetails]:
        """Get all form submissions with pagination and filtering."""
        offset = (page - 1) * page_size
        
        # Build the base query
        query = """
            SELECT 
                s.*,
                ft.name as template_name,
                u.email as user_email
            FROM form_submissions s
            JOIN form_templates ft ON s.template_id = ft.id
            JOIN users u ON s.user_id = u.id
            WHERE 1=1
        """
        params = {}
        
        # Add filters
        if user_id:
            query += " AND s.user_id = :user_id"
            params["user_id"] = user_id
        if template_id:
            query += " AND s.template_id = :template_id"
            params["template_id"] = template_id
            
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM ({query}) as filtered
        """
        total = await self.db.fetch_val(count_query, params)
        
        # Add pagination
        query += " ORDER BY s.created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = page_size
        params["offset"] = offset
        
        # Execute query
        submissions = await self.db.fetch_all(query, params)
        
        # Convert to SubmissionDetails objects
        items = [
            SubmissionDetails(
                id=sub["id"],
                template_id=sub["template_id"],
                template_name=sub["template_name"],
                user_id=sub["user_id"],
                user_email=sub["user_email"],
                status=sub["status"],
                data=sub["data"],
                created_at=sub["created_at"],
                updated_at=sub["updated_at"],
                error_category=sub["error_category"],
                error_code=sub["error_code"],
                error_details=sub["error_details"],
                processing_started_at=sub["processing_started_at"],
                processing_completed_at=sub["processing_completed_at"],
                processing_duration_ms=sub["processing_duration_ms"],
                retry_count=sub["retry_count"],
                max_retries=sub["max_retries"],
                next_retry_at=sub["next_retry_at"]
            )
            for sub in submissions
        ]
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )

    async def get_system_metrics(self) -> SystemMetrics:
        """Get system-wide metrics."""
        # Get total submissions
        total_submissions = await self.db.fetch_val(
            "SELECT COUNT(*) FROM form_submissions"
        )
        
        # Get error counts by category
        error_counts = await self.db.fetch_all("""
            SELECT 
                error_category,
                COUNT(*) as count
            FROM form_submissions
            WHERE error_category IS NOT NULL
            GROUP BY error_category
        """)
        
        # Get submissions by status
        status_counts = await self.db.fetch_all("""
            SELECT 
                status,
                COUNT(*) as count
            FROM form_submissions
            GROUP BY status
        """)
        
        # Calculate average processing time
        avg_processing_time = await self.db.fetch_val("""
            SELECT AVG(processing_duration_ms)
            FROM form_submissions
            WHERE processing_duration_ms IS NOT NULL
        """)
        
        return SystemMetrics(
            total_submissions=total_submissions,
            error_counts={e["error_category"]: e["count"] for e in error_counts},
            status_counts={s["status"]: s["count"] for s in status_counts},
            avg_processing_time_ms=avg_processing_time or 0
        )

    async def get_admin_actions(
        self,
        page: int = 1,
        page_size: int = 20,
        admin_id: Optional[UUID] = None
    ) -> PaginatedResponse[AdminAction]:
        """Get admin action history."""
        offset = (page - 1) * page_size
        
        # Build the base query
        query = """
            SELECT 
                a.*,
                u.email as admin_email
            FROM admin_actions a
            JOIN users u ON a.admin_id = u.id
            WHERE 1=1
        """
        params = {}
        
        # Add filters
        if admin_id:
            query += " AND a.admin_id = :admin_id"
            params["admin_id"] = admin_id
            
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM ({query}) as filtered
        """
        total = await self.db.fetch_val(count_query, params)
        
        # Add pagination
        query += " ORDER BY a.created_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = page_size
        params["offset"] = offset
        
        # Execute query
        actions = await self.db.fetch_all(query, params)
        
        # Convert to AdminAction objects
        items = [
            AdminAction(
                id=action["id"],
                admin_id=action["admin_id"],
                admin_email=action["admin_email"],
                action=action["action"],
                entity_type=action["entity_type"],
                entity_id=action["entity_id"],
                details=action["details"],
                created_at=action["created_at"]
            )
            for action in actions
        ]
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )

    async def _log_admin_action(self, action: AdminActionCreate) -> None:
        """Log an admin action."""
        query = """
            INSERT INTO admin_actions (
                admin_id,
                action,
                entity_type,
                entity_id,
                details,
                created_at
            ) VALUES (
                :admin_id,
                :action,
                :entity_type,
                :entity_id,
                :details,
                NOW()
            )
        """
        await self.db.execute(query, action.dict()) 