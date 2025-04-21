"""
Service for tracking form submissions in the database with robust error handling and retries.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import uuid
import asyncio
from functools import wraps
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from app.models.form_submission import FormSubmission

logger = logging.getLogger(__name__)

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying operations on failure"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}. "
                            f"Retrying in {wait_time} seconds. Error: {str(e)}"
                        )
                        await asyncio.sleep(wait_time)
            raise last_error
        return wrapper
    return decorator

class SubmissionTracker:
    """Service for tracking form submissions with robust error handling"""
    
    def __init__(
        self, 
        supabase_url: str, 
        supabase_key: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30
    ):
        """Initialize the submission tracker with configuration"""
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # Initialize Supabase client with retry options
        options = ClientOptions(
            schema='public',
            headers={
                'X-Client-Info': 'paper-trail-automator',
                'X-Client-Version': '1.0.0'
            }
        )
        self.supabase: Client = create_client(
            supabase_url, 
            supabase_key,
            options=options
        )
        
    @retry_on_error(max_retries=3, delay=1.0)
    async def create_submission(self, submission: FormSubmission) -> FormSubmission:
        """Create a new submission record with retries"""
        try:
            # Ensure required fields are set
            if not submission.id:
                submission.id = str(uuid.uuid4())
            if not submission.created_at:
                submission.created_at = datetime.utcnow()
            if not submission.updated_at:
                submission.updated_at = submission.created_at
                
            # Add creation event
            submission.add_event("created", {
                "user_id": submission.user_id,
                "form_id": submission.form_id
            })
            
            # Insert into database
            data = submission.dict(exclude_none=True)
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: self.supabase.table('form_submissions')
                    .insert(data)
                    .execute()
                ),
                timeout=self.timeout
            )
            
            if result.error:
                raise Exception(f"Failed to create submission: {result.error}")
                
            return FormSubmission(**result.data[0])
            
        except asyncio.TimeoutError:
            logger.error("Timeout while creating submission")
            raise Exception("Database operation timed out")
        except Exception as e:
            logger.error(f"Error creating submission: {str(e)}", exc_info=True)
            raise
        
    @retry_on_error(max_retries=3, delay=1.0)
    async def update_submission(
        self, 
        submission_id: str, 
        updates: Dict[str, Any],
        add_event: bool = True
    ) -> FormSubmission:
        """Update an existing submission record with retries"""
        try:
            # Ensure updated_at is set
            updates['updated_at'] = datetime.utcnow()
            
            # Add update event if requested
            if add_event and "status" in updates:
                event_data = {
                    "old_status": None,  # Will be filled from current record
                    "new_status": updates["status"]
                }
                current = await self.get_submission(submission_id)
                if current:
                    event_data["old_status"] = current.status
                
                updates["events"] = current.events if current else []
                updates["events"].append({
                    "type": "status_changed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": event_data
                })
            
            # Update in database
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: self.supabase.table('form_submissions')
                    .update(updates)
                    .eq('id', submission_id)
                    .execute()
                ),
                timeout=self.timeout
            )
            
            if result.error:
                raise Exception(f"Failed to update submission: {result.error}")
                
            return FormSubmission(**result.data[0])
            
        except asyncio.TimeoutError:
            logger.error("Timeout while updating submission")
            raise Exception("Database operation timed out")
        except Exception as e:
            logger.error(f"Error updating submission: {str(e)}", exc_info=True)
            raise
        
    @retry_on_error(max_retries=3, delay=1.0)
    async def get_submission(self, submission_id: str) -> Optional[FormSubmission]:
        """Get a submission by ID with retries"""
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: self.supabase.table('form_submissions')
                    .select('*')
                    .eq('id', submission_id)
                    .eq('is_deleted', False)
                    .execute()
                ),
                timeout=self.timeout
            )
            
            if result.error:
                raise Exception(f"Failed to get submission: {result.error}")
                
            if not result.data:
                return None
                
            return FormSubmission(**result.data[0])
            
        except asyncio.TimeoutError:
            logger.error("Timeout while getting submission")
            raise Exception("Database operation timed out")
        except Exception as e:
            logger.error(f"Error getting submission: {str(e)}", exc_info=True)
            raise
        
    @retry_on_error(max_retries=3, delay=1.0)
    async def list_submissions(
        self, 
        user_id: str, 
        limit: int = 10, 
        offset: int = 0,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[FormSubmission], int]:
        """List submissions for a user with filtering and pagination"""
        try:
            # Build query
            query = self.supabase.table('form_submissions').select('*', count='exact')
            
            # Apply filters
            query = query.eq('user_id', user_id).eq('is_deleted', False)
            
            if status:
                query = query.eq('status', status)
            if start_date:
                query = query.gte('created_at', start_date.isoformat())
            if end_date:
                query = query.lte('created_at', end_date.isoformat())
                
            # Apply pagination
            query = query.order('created_at', desc=True).limit(limit).offset(offset)
            
            # Execute query
            result = await asyncio.wait_for(
                asyncio.to_thread(lambda: query.execute()),
                timeout=self.timeout
            )
            
            if result.error:
                raise Exception(f"Failed to list submissions: {result.error}")
                
            submissions = [FormSubmission(**item) for item in result.data]
            total_count = result.count if hasattr(result, 'count') else len(submissions)
            
            return submissions, total_count
            
        except asyncio.TimeoutError:
            logger.error("Timeout while listing submissions")
            raise Exception("Database operation timed out")
        except Exception as e:
            logger.error(f"Error listing submissions: {str(e)}", exc_info=True)
            raise
        
    @retry_on_error(max_retries=3, delay=1.0)
    async def delete_submission(self, submission_id: str, hard_delete: bool = False) -> bool:
        """Delete a submission (soft delete by default)"""
        try:
            if hard_delete:
                # Hard delete
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self.supabase.table('form_submissions')
                        .delete()
                        .eq('id', submission_id)
                        .execute()
                    ),
                    timeout=self.timeout
                )
            else:
                # Soft delete
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self.supabase.table('form_submissions')
                        .update({
                            'is_deleted': True,
                            'deleted_at': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat()
                        })
                        .eq('id', submission_id)
                        .execute()
                    ),
                    timeout=self.timeout
                )
            
            if result.error:
                raise Exception(f"Failed to delete submission: {result.error}")
                
            return True
            
        except asyncio.TimeoutError:
            logger.error("Timeout while deleting submission")
            raise Exception("Database operation timed out")
        except Exception as e:
            logger.error(f"Error deleting submission: {str(e)}", exc_info=True)
            raise
            
    async def retry_failed_submissions(self, max_age_hours: int = 24) -> List[FormSubmission]:
        """Retry failed submissions that are within the age limit"""
        try:
            # Get failed submissions
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: self.supabase.table('form_submissions')
                    .select('*')
                    .eq('status', 'failed')
                    .eq('is_deleted', False)
                    .gte('created_at', cutoff_time.isoformat())
                    .execute()
                ),
                timeout=self.timeout
            )
            
            if result.error:
                raise Exception(f"Failed to get failed submissions: {result.error}")
                
            retried_submissions = []
            for submission_data in result.data:
                submission = FormSubmission(**submission_data)
                if submission.can_retry() and submission.prepare_for_retry():
                    updated = await self.update_submission(
                        submission.id,
                        submission.dict(exclude_none=True)
                    )
                    retried_submissions.append(updated)
                    
            return retried_submissions
            
        except asyncio.TimeoutError:
            logger.error("Timeout while retrying failed submissions")
            raise Exception("Database operation timed out")
        except Exception as e:
            logger.error(f"Error retrying failed submissions: {str(e)}", exc_info=True)
            raise 