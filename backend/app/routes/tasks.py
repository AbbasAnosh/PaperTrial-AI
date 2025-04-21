"""
API router for task management.
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query, Body
from typing import Dict, Any, List, Optional
from app.core.celery_app import celery_app
from app.core.auth import get_current_user
from app.models.user import User
from app.db.supabase_client import get_supabase_client
from app.services.task_service import TaskService
from app.models.task import Task, TaskCreate, TaskUpdate
from app.core.errors import ValidationError, NotFoundError, ProcessingError
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of a background task
    """
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'status': 'Task is waiting for execution'
            }
        elif task.state == 'STARTED':
            response = {
                'state': task.state,
                'status': 'Task is being executed'
            }
        elif task.state == 'SUCCESS':
            response = {
                'state': task.state,
                'status': 'Task completed successfully',
                'result': task.result
            }
        elif task.state == 'FAILURE':
            response = {
                'state': task.state,
                'status': 'Task failed',
                'error': str(task.result)
            }
        else:
            response = {
                'state': task.state,
                'status': 'Unknown task state'
            }
            
        return response
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get task status"
        )

@router.post("", response_model=Task, status_code=201)
async def create_task(
    task_create: TaskCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new task
    """
    try:
        supabase = get_supabase_client()
        task_service = TaskService(supabase)
        task = await task_service.create_task(task_create, current_user.id)
        return task
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create task"
        )

@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a task by ID
    """
    try:
        supabase = get_supabase_client()
        task_service = TaskService(supabase)
        task = await task_service.get_task_by_id(task_id, current_user.id)
        if not task:
            raise NotFoundError(f"Task with ID {task_id} not found")
        return task
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting task: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get task"
        )

@router.get("", response_model=List[Task])
async def get_user_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Get all tasks for the current user
    """
    try:
        supabase = get_supabase_client()
        task_service = TaskService(supabase)
        tasks = await task_service.get_user_tasks(current_user.id, skip=skip, limit=limit)
        return tasks
    except Exception as e:
        logger.error(f"Error getting user tasks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get user tasks"
        )

@router.post("/{task_id}/cancel", response_model=Task)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a task
    """
    try:
        supabase = get_supabase_client()
        task_service = TaskService(supabase)
        task = await task_service.cancel_task(task_id, current_user.id)
        if not task:
            raise NotFoundError(f"Task with ID {task_id} not found")
        return task
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error canceling task: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel task"
        )

@router.post("/{task_id}/retry", response_model=Task)
async def retry_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Retry a failed task
    """
    try:
        supabase = get_supabase_client()
        task_service = TaskService(supabase)
        task = await task_service.retry_task(task_id, current_user.id)
        if not task:
            raise NotFoundError(f"Task with ID {task_id} not found")
        return task
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrying task: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retry task"
        ) 