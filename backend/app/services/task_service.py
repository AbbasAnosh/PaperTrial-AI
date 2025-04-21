from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from app.models.task_run import TaskRun, TaskStatus, TaskType, TaskStep
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)

class TaskService:
    """Service for managing task runs in Supabase"""
    
    def __init__(self):
        self.table = "task_runs"
    
    async def create_task(
        self,
        user_id: str,
        task_type: TaskType,
        input_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskRun:
        """Create a new task run"""
        try:
            task = TaskRun(
                user_id=user_id,
                task_type=task_type,
                input_data=input_data,
                metadata=metadata or {}
            )
            
            result = await supabase_client.table(self.table).insert(task.dict()).execute()
            return TaskRun(**result.data[0])
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise
    
    async def get_task(self, task_id: str) -> Optional[TaskRun]:
        """Get a task run by ID"""
        try:
            result = await supabase_client.table(self.table).select("*").eq("id", task_id).execute()
            if not result.data:
                return None
            return TaskRun(**result.data[0])
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {str(e)}")
            raise
    
    async def get_user_tasks(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[TaskRun]:
        """Get tasks for a user"""
        try:
            result = await supabase_client.table(self.table)\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            return [TaskRun(**task) for task in result.data]
        except Exception as e:
            logger.error(f"Error getting tasks for user {user_id}: {str(e)}")
            raise
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        current_step: Optional[TaskStep] = None,
        progress: Optional[float] = None
    ) -> TaskRun:
        """Update task status and progress"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if current_step:
                update_data["current_step"] = current_step
            if progress is not None:
                update_data["progress"] = progress
                
            if status == TaskStatus.PROCESSING and not await self.get_task(task_id).started_at:
                update_data["started_at"] = datetime.utcnow().isoformat()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                update_data["completed_at"] = datetime.utcnow().isoformat()

            result = await supabase_client.table(self.table)\
                .update(update_data)\
                .eq("id", task_id)\
                .execute()
            return TaskRun(**result.data[0])
        except Exception as e:
            logger.error(f"Error updating task {task_id} status: {str(e)}")
            raise
    
    async def update_task_output(
        self,
        task_id: str,
        output_data: Dict[str, Any]
    ) -> TaskRun:
        """Update task output data"""
        try:
            result = await supabase_client.table(self.table)\
                .update({
                    "output_data": output_data,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", task_id)\
                .execute()
            return TaskRun(**result.data[0])
        except Exception as e:
            logger.error(f"Error updating task {task_id} output: {str(e)}")
            raise
    
    async def fail_task(
        self,
        task_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> TaskRun:
        """Mark a task as failed"""
        try:
            result = await supabase_client.table(self.table)\
                .update({
                    "status": TaskStatus.FAILED,
                    "error_message": error_message,
                    "error_details": error_details,
                    "completed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", task_id)\
                .execute()
            return TaskRun(**result.data[0])
        except Exception as e:
            logger.error(f"Error failing task {task_id}: {str(e)}")
            raise
    
    async def retry_task(self, task_id: str) -> TaskRun:
        """Increment retry count and update status to retrying"""
        try:
            task = await self.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            result = await supabase_client.table(self.table)\
                .update({
                    "status": TaskStatus.RETRYING,
                    "retry_count": task.retry_count + 1,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", task_id)\
                .execute()
            return TaskRun(**result.data[0])
        except Exception as e:
            logger.error(f"Error retrying task {task_id}: {str(e)}")
            raise
    
    async def cancel_task(self, task_id: str) -> TaskRun:
        """Mark a task as cancelled"""
        try:
            result = await supabase_client.table(self.table)\
                .update({
                    "status": TaskStatus.CANCELLED,
                    "completed_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", task_id)\
                .execute()
            return TaskRun(**result.data[0])
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {str(e)}")
            raise 