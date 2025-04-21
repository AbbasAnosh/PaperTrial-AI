from celery import shared_task
from app.services.form_agent import FormAgent
from app.services.submission_tracker import SubmissionTracker
from app.services.storage_service import StorageService
import logging
from app.core.celery_app import celery_app, supabase
from app.services.form_service import FormService
from app.services.mapping_service import MappingService
from app.core.errors import ProcessingError
from datetime import datetime

logger = logging.getLogger(__name__)

@shared_task
async def process_form_submission(submission_id: str, form_id: str, user_data: dict, documents: dict):
    """Process a form submission asynchronously"""
    try:
        submission_tracker = SubmissionTracker()
        storage_service = StorageService()
        form_agent = FormAgent()

        # Update status to processing
        await submission_tracker.update_submission_status(
            submission_id,
            "processing",
            "Form is being processed"
        )

        # Process the form
        result = await form_agent.process_form(form_id, user_data, documents)

        # Store any generated files
        if "screenshot" in result:
            screenshot_url = await storage_service.upload_file(
                result["screenshot"],
                f"submissions/{submission_id}/screenshot.png"
            )
            result["screenshot_url"] = screenshot_url

        # Update submission with results
        await submission_tracker.add_submission_event(
            submission_id,
            "form_processed",
            result
        )

        # Update final status
        await submission_tracker.update_submission_status(
            submission_id,
            result["status"],
            "Form processing completed" if result["status"] == "success" else f"Form processing failed: {result.get('error', 'Unknown error')}"
        )

        return result

    except Exception as e:
        logging.error(f"Error processing form submission: {str(e)}", exc_info=True)
        await submission_tracker.update_submission_status(
            submission_id,
            "failed",
            f"Error processing form: {str(e)}"
        )
        raise 

@celery_app.task(bind=True, max_retries=3)
def process_form_task(self, form_data: dict, user_id: str):
    """
    Process a form submission in the background
    """
    try:
        form_service = FormService()
        mapping_service = MappingService()
        
        # Map form fields
        mapped_fields = mapping_service.map_fields(form_data)
        
        # Process the form
        result = form_service.process_form(mapped_fields, user_id)
        
        # Store form submission in Supabase
        timestamp = datetime.utcnow().isoformat()
        submission_data = {
            "user_id": user_id,
            "form_data": form_data,
            "mapped_fields": mapped_fields,
            "result": result,
            "created_at": timestamp
        }
        
        # Insert into form_submissions table
        supabase.table("form_submissions").insert(submission_data).execute()
        
        return {
            "status": "success",
            "result": result,
            "submission_id": submission_data.get("id")
        }
    except Exception as e:
        logger.error(f"Error processing form: {str(e)}")
        self.retry(exc=e, countdown=30)  # Retry after 30 seconds

@celery_app.task(bind=True)
def auto_map_fields_task(self, form_id: str, user_id: str):
    """
    Automatically map form fields using AI
    """
    try:
        form_service = FormService()
        mapping_service = MappingService()
        
        # Get form template from Supabase
        template = supabase.table("form_templates").select("*").eq("id", form_id).single().execute()
        
        # Auto-map fields
        mapped_fields = mapping_service.auto_map_fields(template.data)
        
        # Update template with mapped fields in Supabase
        supabase.table("form_templates").update({
            "mapped_fields": mapped_fields,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", form_id).execute()
        
        return {
            "status": "success",
            "mapped_fields": mapped_fields
        }
    except Exception as e:
        logger.error(f"Error auto-mapping fields: {str(e)}")
        raise ProcessingError("Failed to auto-map form fields") 