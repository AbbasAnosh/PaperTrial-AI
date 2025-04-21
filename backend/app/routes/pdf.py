from fastapi import Depends, HTTPException, status, UploadFile, File
from typing import Dict, Any, List
from app.services.pdf_processor import PDFProcessor
from app.core.auth import get_current_user
from app.api.base import BaseRouter
from app.core.errors import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)
router = BaseRouter(prefix="/pdf", tags=["pdf"])

# Initialize PDF processor
pdf_processor = PDFProcessor()

# Define route handlers
@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Upload a PDF file"""
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
            
        # Process the PDF
        result = await pdf_processor.process_pdf(file, current_user["user_id"])
        return result
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing PDF file"
        )

@router.get("/{pdf_id}")
async def get_pdf(
    pdf_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get PDF information"""
    try:
        result = await pdf_processor.get_pdf(pdf_id, current_user["user_id"])
        if not result:
            raise NotFoundError(f"PDF with ID {pdf_id} not found")
        return result
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving PDF"
        )

@router.delete("/{pdf_id}")
async def delete_pdf(
    pdf_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete a PDF"""
    try:
        success = await pdf_processor.delete_pdf(pdf_id, current_user["user_id"])
        if not success:
            raise NotFoundError(f"PDF with ID {pdf_id} not found")
        return {"message": "PDF deleted successfully"}
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting PDF"
        ) 