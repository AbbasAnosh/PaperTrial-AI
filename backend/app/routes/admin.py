from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from app.models.admin import (
    PaginatedResponse,
    SubmissionDetails,
    SystemMetrics,
    AdminAction
)
from app.services.admin_service import AdminService
from app.core.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/submissions", response_model=PaginatedResponse[SubmissionDetails])
async def get_all_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    template_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    admin_service: AdminService = Depends()
):
    """Get all form submissions with pagination and filtering."""
    if not await admin_service.is_admin(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return await admin_service.get_all_submissions(
        page=page,
        page_size=page_size,
        user_id=user_id,
        template_id=template_id
    )

@router.get("/submissions/{submission_id}", response_model=SubmissionDetails)
async def get_submission_details(
    submission_id: UUID,
    current_user = Depends(get_current_user),
    admin_service: AdminService = Depends()
):
    """Get detailed information about a specific submission."""
    if not await admin_service.is_admin(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    submission = await admin_service.get_submission_details(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return submission

@router.post("/submissions/{submission_id}/retry")
async def retry_submission(
    submission_id: UUID,
    current_user = Depends(get_current_user),
    admin_service: AdminService = Depends()
):
    """Retry a failed submission."""
    if not await admin_service.is_admin(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await admin_service.retry_submission(submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found or cannot be retried")
    
    return {"message": "Submission retry initiated"}

@router.delete("/submissions/{submission_id}")
async def force_delete_submission(
    submission_id: UUID,
    current_user = Depends(get_current_user),
    admin_service: AdminService = Depends()
):
    """Force delete a submission."""
    if not await admin_service.is_admin(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await admin_service.force_delete_submission(submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {"message": "Submission deleted"}

@router.get("/submissions/{submission_id}/logs")
async def get_submission_logs(
    submission_id: UUID,
    current_user = Depends(get_current_user),
    admin_service: AdminService = Depends()
):
    """Get logs for a specific submission."""
    if not await admin_service.is_admin(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    logs = await admin_service.get_submission_logs(submission_id)
    if not logs:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return logs

@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics(
    current_user = Depends(get_current_user),
    admin_service: AdminService = Depends()
):
    """Get system-wide metrics."""
    if not await admin_service.is_admin(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return await admin_service.get_system_metrics()

@router.get("/actions", response_model=PaginatedResponse[AdminAction])
async def get_admin_actions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin_id: Optional[UUID] = None,
    current_user = Depends(get_current_user),
    admin_service: AdminService = Depends()
):
    """Get admin action history."""
    if not await admin_service.is_admin(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return await admin_service.get_admin_actions(
        page=page,
        page_size=page_size,
        admin_id=admin_id
    ) 