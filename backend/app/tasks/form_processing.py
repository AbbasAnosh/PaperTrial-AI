from celery import shared_task
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

from ..services.form_service import FormService
from ..models.form_submission import FormSubmission
from ..database import get_db

logger = logging.getLogger(__name__)

@shared_task(
    name='process-form-submission',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def process_form_submission(
    self,
    submission_id: str,
    template_id: str,
    data: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """
    Process a form submission asynchronously.
    
    Args:
        submission_id: The ID of the submission to process
        template_id: The ID of the form template
        data: The form submission data
        user_id: The ID of the user who submitted the form
        
    Returns:
        Dict containing the processing result
    """
    try:
        form_service = FormService()
        db = get_db()
        
        # Get the submission
        submission = db.query(FormSubmission).filter(
            FormSubmission.id == submission_id
        ).first()
        
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
            
        # Update submission status to processing
        submission.status = 'processing'
        submission.processing_started_at = datetime.utcnow()
        db.commit()
        
        # Process the submission
        result = form_service._process_submission(
            submission_id=submission_id,
            template_id=template_id,
            data=data,
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing submission {submission_id}: {str(e)}")
        
        # Update submission with error
        if submission:
            submission.status = 'failed'
            submission.error_category = 'system'
            submission.error_code = 'PROCESSING_ERROR'
            submission.error_details = {
                'message': str(e),
                'traceback': self.request.get_exc_info()
            }
            submission.processing_completed_at = datetime.utcnow()
            db.commit()
            
        # Retry the task if appropriate
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
            
        return {
            'status': 'failed',
            'error': str(e)
        }

@shared_task(name='retry-failed-submissions')
def retry_failed_submissions() -> Dict[str, Any]:
    """
    Retry failed submissions that haven't exceeded their retry limit.
    
    Returns:
        Dict containing the retry results
    """
    try:
        form_service = FormService()
        db = get_db()
        
        # Get failed submissions that are ready for retry
        failed_submissions = db.query(FormSubmission).filter(
            FormSubmission.status == 'failed',
            FormSubmission.retry_count < FormSubmission.max_retries,
            FormSubmission.next_retry_at <= datetime.utcnow()
        ).all()
        
        results = {
            'total': len(failed_submissions),
            'retried': 0,
            'errors': []
        }
        
        for submission in failed_submissions:
            try:
                # Retry the submission
                process_form_submission.delay(
                    submission_id=str(submission.id),
                    template_id=str(submission.template_id),
                    data=submission.data,
                    user_id=str(submission.user_id)
                )
                
                # Update submission retry count
                submission.retry_count += 1
                submission.last_retry_at = datetime.utcnow()
                submission.next_retry_at = None
                db.commit()
                
                results['retried'] += 1
                
            except Exception as e:
                logger.error(f"Error retrying submission {submission.id}: {str(e)}")
                results['errors'].append({
                    'submission_id': str(submission.id),
                    'error': str(e)
                })
                
        return results
        
    except Exception as e:
        logger.error(f"Error in retry_failed_submissions: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        } 