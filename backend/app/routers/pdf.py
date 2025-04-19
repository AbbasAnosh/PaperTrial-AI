from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Optional
from app.services.pdf_service import PDFService
from app.routers.auth import get_current_user

router = APIRouter(prefix="/pdf", tags=["pdf"])

@router.post("/process")
async def process_pdf(
    file: UploadFile = File(...),
    form_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        pdf_service = PDFService()
        file_data = await file.read()
        
        document = await pdf_service.process_pdf(
            file_data=file_data,
            filename=file.filename,
            form_type=form_type or "unknown",
            user_email=current_user["email"]
        )
        
        return {
            "message": "PDF processed successfully",
            "document": document
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        pdf_service = PDFService()
        url = await pdf_service.get_pdf_url(document_id, current_user["email"])
        
        if not url:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{document_id}/status")
async def update_document_status(
    document_id: str,
    status: str,
    extracted_fields: Optional[dict] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        pdf_service = PDFService()
        document = await pdf_service.update_document_status(
            document_id=document_id,
            user_email=current_user["email"],
            status=status,
            extracted_fields=extracted_fields
        )
        
        return {
            "message": "Document status updated successfully",
            "document": document
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 