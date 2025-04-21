"""
Form routes for handling form templates, submissions, and PDF processing.
"""

from fastapi import Depends, HTTPException, status, Query, Path, UploadFile, File, Body
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
from app.core.security import get_current_user
from app.database.session import get_supabase
from app.api.base import BaseRouter
from app.core.auth import get_current_user
from app.models.user import User
import logging
from app.core.errors import (
    NotFoundError,
    ValidationError,
    ProcessingError,
    DatabaseError
)
from app.models.token import Token
import secrets
import os

logger = logging.getLogger(__name__)
router = BaseRouter(prefix="", tags=["forms"])

# Initialize PDF processor
pdf_processor = PDFProcessor()

# Define route handlers
async def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    active_only: bool = Query(True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """List form templates with pagination."""
    form_service = FormService(supabase)
    return await form_service.list_templates(skip=skip, limit=limit, active_only=active_only)

async def get_template(
    template_id: str = Path(..., description="The ID of the template to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Get a form template by ID."""
    form_service = FormService(supabase)
    template = await form_service.get_template_by_id(template_id)
    if not template:
        raise NotFoundError(f"Template with ID {template_id} not found")
    return template

async def create_template(
    template_create: FormTemplateCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Create a new form template."""
    form_service = FormService(supabase)
    try:
        return await form_service.create_template(template_create, current_user["user_id"])
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise ValidationError(str(e))

@router.post("/process-pdf")
async def process_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    supabase = Depends(get_supabase)
) -> Dict[str, Any]:
    """
    Process a PDF file and extract form fields.
    
    Args:
        file: The PDF file to process
        current_user: The authenticated user
        supabase: Supabase client
        
    Returns:
        Dict containing the form ID and extracted fields
    """
    try:
        # Validate file type
        if not file.content_type == "application/pdf":
            raise ValidationError("Only PDF files are allowed")
            
        # Validate file size (10MB limit)
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
            if file_size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError("File size exceeds 10MB limit")
        
        # Reset file pointer
        await file.seek(0)
        
        # Save file to temporary location
        temp_file_path = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # Upload to Supabase storage
        storage_path = f"pdfs/{current_user.id}/{file.filename}"
        with open(temp_file_path, "rb") as f:
            supabase.storage.from_("forms").upload(
                storage_path,
                f.read(),
                {"content-type": "application/pdf"}
            )
            
        # Get public URL
        file_url = supabase.storage.from_("forms").get_public_url(storage_path)
        
        # Process PDF and extract fields
        fields = await pdf_processor.process_pdf(temp_file_path)
        
        # Create form template
        template = await create_template(
            name=file.filename,
            file_url=file_url,
            fields=fields,
            user_id=current_user.id
        )
        
        # Clean up temporary file
        os.remove(temp_file_path)
        
        return {
            "id": template.id,
            "fields": fields
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process PDF file"
        )

async def process_web_form(
    url: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Process a web form and extract form fields."""
    try:
        form_service = FormService(supabase)
        result = await form_service.process_web_form(url, current_user["user_id"])
        
        return {
            "url": url,
            "fields": result
        }
    except Exception as e:
        logger.error(f"Error processing web form: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{form_id}", response_model=Dict[str, Any])
async def get_form(
    form_id: str = Path(..., description="The ID of the form to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Get a form by ID."""
    form_service = FormService(supabase)
    try:
        form = await form_service.get_form_by_id(form_id, current_user["user_id"])
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Form with ID {form_id} not found"
            )
        return form
    except Exception as e:
        logger.error(f"Error retrieving form: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{form_id}", response_model=Dict[str, Any])
async def update_form(
    form_id: str = Path(..., description="The ID of the form to update"),
    fields: List[Dict[str, Any]] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Update a form's fields."""
    form_service = FormService(supabase)
    try:
        form = await form_service.update_form_fields(form_id, fields, current_user["user_id"])
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Form with ID {form_id} not found"
            )
        return form
    except Exception as e:
        logger.error(f"Error updating form: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form(
    form_id: str = Path(..., description="The ID of the form to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Delete a form."""
    form_service = FormService(supabase)
    try:
        success = await form_service.delete_form(form_id, current_user["user_id"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Form with ID {form_id} not found"
            )
    except Exception as e:
        logger.error(f"Error deleting form: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/submissions", response_model=FormSubmission, status_code=status.HTTP_201_CREATED)
async def create_submission(
    submission_create: FormSubmissionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Create a new form submission."""
    form_service = FormService(supabase)
    try:
        return await form_service.create_submission(submission_create, current_user["user_id"])
    except Exception as e:
        logger.error(f"Error creating submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/submissions", response_model=List[FormSubmission])
async def list_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """List form submissions with pagination."""
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
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Get a form submission by ID."""
    form_service = FormService(supabase)
    try:
        submission = await form_service.get_submission_by_id(submission_id, current_user["user_id"])
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submission with ID {submission_id} not found"
            )
        return submission
    except Exception as e:
        logger.error(f"Error retrieving submission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/templates/{template_id}/auto-map", response_model=List[Dict[str, Any]])
async def auto_map_fields(
    template_id: str = Path(..., description="The ID of the template to map fields for"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Similarity threshold for auto-mapping"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Automatically map extracted fields to form fields."""
    form_service = FormService(supabase)
    mapping_service = MappingService(supabase, PDFProcessor())
    
    try:
        # Get the template
        template = await form_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {template_id} not found"
            )
        
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Register routes
router.add_api_route("/templates", list_templates, methods=["GET"], response_model=List[FormTemplate])
router.add_api_route("/templates/{template_id}", get_template, methods=["GET"], response_model=FormTemplate)
router.add_api_route("/templates", create_template, methods=["POST"], response_model=FormTemplate, status_code=status.HTTP_201_CREATED)
router.add_api_route("/process-pdf", process_pdf, methods=["POST"], response_model=Dict[str, Any])
router.add_api_route("/process-web", process_web_form, methods=["POST"], response_model=Dict[str, Any]) 