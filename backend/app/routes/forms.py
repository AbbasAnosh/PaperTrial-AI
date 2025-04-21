"""
API router for form templates and submissions.
"""

from fastapi import Depends, HTTPException, status, Query, Path, UploadFile, File, Body, BackgroundTasks
from typing import List, Optional, Dict, Any
from app.models.form_template import (
    FormTemplate, 
    FormTemplateCreate, 
    FormTemplateUpdate,
    FormSubmission,
    FormSubmissionCreate
)
from app.services.form_service import FormService
from app.services.mapping_service import MappingService
from app.services.pdf_processor import PDFProcessor
from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_client
from app.core.errors import ValidationError, NotFoundError, ProcessingError
import logging
import os
import time
from app.tasks.pdf_processing import process_pdf_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forms", tags=["forms"])

# Initialize services
pdf_processor = PDFProcessor()

# Template routes
@router.get("/templates", response_model=List[FormTemplate])
async def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    active_only: bool = Query(True),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List form templates with pagination."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    return await form_service.list_templates(skip=skip, limit=limit, active_only=active_only)

@router.get("/templates/{template_id}", response_model=FormTemplate)
async def get_template(
    template_id: str = Path(..., description="The ID of the template to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a form template by ID."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    template = await form_service.get_template_by_id(template_id)
    if not template:
        raise NotFoundError(f"Template with ID {template_id} not found")
    return template

@router.post("/templates", response_model=FormTemplate, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_create: FormTemplateCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new form template."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    try:
        return await form_service.create_template(template_create, current_user["user_id"])
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise ValidationError(str(e))

@router.put("/templates/{template_id}", response_model=FormTemplate)
async def update_template(
    template_update: FormTemplateUpdate,
    template_id: str = Path(..., description="The ID of the template to update"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a form template."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    try:
        template = await form_service.update_template(template_id, template_update)
        if not template:
            raise NotFoundError(f"Template with ID {template_id} not found")
        return template
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}")
        raise ValidationError(str(e))

@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str = Path(..., description="The ID of the template to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a form template."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    try:
        success = await form_service.delete_template(template_id)
        if not success:
            raise NotFoundError(f"Template with ID {template_id} not found")
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        raise ValidationError(str(e))

@router.post("/process-pdf", response_model=Dict[str, Any])
async def process_pdf(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Process a PDF file and extract form fields."""
    temp_file_path = None
    try:
        # Validate file type
        if not file.content_type or not file.content_type.lower() == "application/pdf":
            raise ValidationError("Only PDF files are allowed")
            
        # Validate file size (10MB limit)
        file_size = 0
        content = await file.read()
        file_size = len(content)
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise ValidationError("File size exceeds 10MB limit")
        
        # Save file to temporary location with unique name
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f"{current_user['user_id']}_{int(time.time())}_{file.filename}")
        
        with open(temp_file_path, "wb") as buffer:
            buffer.write(content)
            
        # Upload to Supabase storage with unique path
        supabase = get_supabase_client()
        storage_path = f"pdfs/{current_user['user_id']}/{int(time.time())}_{file.filename}"
        with open(temp_file_path, "rb") as f:
            supabase.storage.from_("forms").upload(
                storage_path,
                f.read(),
                {"content-type": "application/pdf"}
            )
            
        # Get public URL
        file_url = supabase.storage.from_("forms").get_public_url(storage_path)
        
        # Start Celery task for processing
        task = process_pdf_task.delay(temp_file_path, current_user["user_id"])
        
        return {
            "task_id": task.id,
            "status": "processing",
            "file_path": storage_path,
            "file_url": file_url,
            "message": "PDF processing started in background"
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise ProcessingError(str(e))

@router.get("/task-status/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get the status of a PDF processing task."""
    try:
        task = process_pdf_task.AsyncResult(task_id)
        response = {
            "task_id": task_id,
            "status": task.status,
            "result": task.result if task.status == "SUCCESS" else None,
            "error": str(task.result) if task.status == "FAILURE" else None
        }
        return response
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise ProcessingError(str(e))

@router.post("/process-web", response_model=Dict[str, Any])
async def process_web_form(
    url: str = Body(..., embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Process a web form and extract form fields."""
    try:
        supabase = get_supabase_client()
        form_service = FormService(supabase)
        result = await form_service.process_web_form(url, current_user["user_id"])
        return result
    except Exception as e:
        logger.error(f"Error processing web form: {str(e)}")
        raise ProcessingError(str(e))

# Form submission routes
@router.post("/submissions", response_model=FormSubmission, status_code=status.HTTP_201_CREATED)
async def create_submission(
    submission_create: FormSubmissionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new form submission."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    try:
        return await form_service.create_submission(submission_create, current_user["user_id"])
    except Exception as e:
        logger.error(f"Error creating submission: {str(e)}")
        raise ValidationError(str(e))

@router.get("/submissions", response_model=List[FormSubmission])
async def list_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List form submissions with pagination."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    return await form_service.list_submissions(
        user_id=current_user["user_id"],
        template_id=template_id,
        skip=skip,
        limit=limit
    )

@router.get("/submissions/{submission_id}", response_model=FormSubmission)
async def get_submission(
    submission_id: str = Path(..., description="The ID of the submission to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a form submission by ID."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    try:
        submission = await form_service.get_submission_by_id(submission_id, current_user["user_id"])
        if not submission:
            raise NotFoundError(f"Submission with ID {submission_id} not found")
        return submission
    except Exception as e:
        logger.error(f"Error retrieving submission: {str(e)}")
        raise ValidationError(str(e))

# Field mapping routes
@router.post("/templates/{template_id}/auto-map", response_model=List[Dict[str, Any]])
async def auto_map_fields(
    template_id: str = Path(..., description="The ID of the template to map fields for"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Similarity threshold for auto-mapping"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Automatically map extracted fields to form fields."""
    supabase = get_supabase_client()
    form_service = FormService(supabase)
    mapping_service = MappingService(supabase, PDFProcessor())
    
    try:
        # Get the template
        template = await form_service.get_template_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template with ID {template_id} not found")
        
        # Get the latest extracted fields from the user's session
        extracted_fields = []  # Replace with actual extracted fields
        
        # Auto-map fields
        mappings = await mapping_service.auto_map_fields(
            template_id=template_id,
            extracted_fields=extracted_fields,
            user_id=current_user["user_id"],
            threshold=threshold
        )
        
        return mappings
    except Exception as e:
        logger.error(f"Error auto-mapping fields: {str(e)}")
        raise ProcessingError(str(e)) 