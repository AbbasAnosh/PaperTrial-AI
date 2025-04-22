from celery import shared_task
from datetime import datetime, timedelta
import logging
from typing import Optional
from app.services.form_service import FormService
from app.config.database import get_db

logger = logging.getLogger(__name__)

@shared_task(
    name='app.tasks.cleanup.cleanup_old_submissions',
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def cleanup_old_submissions(
    self,
    retention_days: Optional[int] = 30,
    batch_size: Optional[int] = 100
) -> dict:
    """
    Clean up old form submissions that have exceeded the retention period.
    
    Args:
        retention_days: Number of days to retain submissions (default: 30)
        batch_size: Number of submissions to process in each batch (default: 100)
        
    Returns:
        dict: Summary of cleanup operation
    """
    try:
        logger.info(f"Starting cleanup of submissions older than {retention_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        db = get_db()
        form_service = FormService(db)
        
        # Get count of submissions to be deleted
        total_count = db.table('form_submissions').select('id', count='exact').lt('created_at', cutoff_date).execute()
        
        if total_count.count == 0:
            logger.info("No submissions found for cleanup")
            return {
                'status': 'success',
                'message': 'No submissions found for cleanup',
                'deleted_count': 0
            }
            
        # Process in batches
        deleted_count = 0
        offset = 0
        
        while offset < total_count.count:
            # Get batch of submissions
            submissions = db.table('form_submissions').select('id').lt('created_at', cutoff_date).range(offset, offset + batch_size - 1).execute()
            
            if not submissions.data:
                break
                
            # Delete submissions
            submission_ids = [sub['id'] for sub in submissions.data]
            result = form_service.delete_submissions(submission_ids)
            
            if result.get('success'):
                deleted_count += len(submission_ids)
                logger.info(f"Deleted {len(submission_ids)} submissions")
            else:
                logger.error(f"Failed to delete submissions: {result.get('error')}")
                
            offset += batch_size
            
        logger.info(f"Cleanup completed. Deleted {deleted_count} submissions")
        return {
            'status': 'success',
            'message': f'Successfully deleted {deleted_count} submissions',
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        self.retry(exc=e) 