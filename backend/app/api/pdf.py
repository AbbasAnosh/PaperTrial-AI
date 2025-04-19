from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List
import aiofiles
import os
from app.core.unstructured_client import UnstructuredClient
from app.core.supabase_client import SupabaseClient
from app.core.auth import get_current_user

router = APIRouter()
unstructured_client = UnstructuredClient()
supabase_client = SupabaseClient()

@router.post("/process")
async def process_pdf(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Save uploaded file temporarily
    temp_path = f"temp_{file.filename}"
    try:
        async with aiofiles.open(temp_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # Process PDF with Unstructured.io
        elements = await unstructured_client.process_pdf(temp_path)
        
        # Store in Supabase
        document_id = await supabase_client.store_document(
            user_id=current_user["id"],
            filename=file.filename,
            elements=elements
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "PDF processed successfully",
                "document_id": document_id,
                "elements": elements
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.get("/documents")
async def get_documents(current_user: dict = Depends(get_current_user)):
    try:
        documents = await supabase_client.get_user_documents(current_user["id"])
        return JSONResponse(
            status_code=200,
            content={"documents": documents}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        document = await supabase_client.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        if document["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
        return JSONResponse(
            status_code=200,
            content={"document": document}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 