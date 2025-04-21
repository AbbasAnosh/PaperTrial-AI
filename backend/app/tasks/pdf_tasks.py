from app.core.celery_app import celery_app, supabase
from app.services.pdf_processor import PDFProcessor
from app.core.errors import ProcessingError
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def process_pdf_task(self, file_path: str, user_id: str):
    """
    Process a PDF file in the background
    """
    try:
        processor = PDFProcessor()
        
        # Process the PDF
        result = processor.process_pdf(file_path)
        
        # Store the processed data in Supabase
        timestamp = datetime.utcnow().isoformat()
        storage_path = f"processed_pdfs/{user_id}/{os.path.basename(file_path)}_{timestamp}.json"
        
        supabase.storage.from_("pdfs").upload(
            storage_path,
            result,
            {"content-type": "application/json"}
        )
        
        # Get the public URL
        public_url = supabase.storage.from_("pdfs").get_public_url(storage_path)
        
        return {
            "status": "success",
            "result": result,
            "storage_path": storage_path,
            "public_url": public_url
        }
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        self.retry(exc=e, countdown=60)  # Retry after 1 minute

@celery_app.task(bind=True)
def generate_pdf_preview_task(self, file_path: str, user_id: str):
    """
    Generate a preview of a PDF file
    """
    try:
        processor = PDFProcessor()
        
        # Generate preview
        preview_path = processor.generate_preview(file_path)
        
        # Store the preview in Supabase
        timestamp = datetime.utcnow().isoformat()
        storage_path = f"previews/{user_id}/{os.path.basename(file_path)}_{timestamp}.png"
        
        with open(preview_path, 'rb') as f:
            supabase.storage.from_("pdfs").upload(
                storage_path,
                f.read(),
                {"content-type": "image/png"}
            )
        
        # Get the public URL
        public_url = supabase.storage.from_("pdfs").get_public_url(storage_path)
        
        # Clean up temporary file
        os.remove(preview_path)
        
        return {
            "status": "success",
            "preview_url": public_url,
            "storage_path": storage_path
        }
    except Exception as e:
        logger.error(f"Error generating PDF preview: {str(e)}")
        raise ProcessingError("Failed to generate PDF preview") 