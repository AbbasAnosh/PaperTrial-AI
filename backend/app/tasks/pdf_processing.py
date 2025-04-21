import os
import logging
from typing import Dict, Any
from celery import Task
from app.core.celery_app import celery_app
from app.services.form_service import FormService
from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)

class PDFProcessingTask(Task):
    _form_service = None
    _supabase = None

    @property
    def form_service(self):
        if self._form_service is None:
            self._form_service = FormService(self.supabase)
        return self._form_service

    @property
    def supabase(self):
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

@celery_app.task(bind=True, base=PDFProcessingTask)
def process_pdf_task(self, file_path: str, user_id: str) -> Dict[str, Any]:
    """Process PDF file and extract form fields."""
    try:
        # Update task state
        self.update_state(state="PROCESSING", meta={"status": "processing"})
        
        # Process PDF and extract fields
        result = self.form_service.process_pdf(file_path, user_id)
        
        # Update task state with success
        self.update_state(
            state="SUCCESS",
            meta={
                "status": "completed",
                "result": result
            }
        )
        
        return {
            "status": "completed",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error in PDF processing task: {str(e)}")
        # Update task state with error
        self.update_state(
            state="FAILURE",
            meta={
                "status": "failed",
                "error": str(e)
            }
        )
        raise
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}") 