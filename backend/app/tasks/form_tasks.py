from celery import shared_task
from app.services.form_agent import FormAgent
from app.services.submission_tracker import SubmissionTracker
from app.services.storage_service import StorageService
import logging

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