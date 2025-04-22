from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from sqlalchemy import func, and_
from app.models.form_submission import FormSubmission
from app.database import get_db

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for tracking and analyzing form processing metrics"""
    
    def get_submission_metrics(self, user_id: str, days: int = 30) -> Dict:
        """
        Get submission metrics for a user
        
        Args:
            user_id: The user ID to get metrics for
            days: Number of days to look back
            
        Returns:
            Dict containing submission metrics
        """
        try:
            db = get_db()
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get total submissions
            total_submissions = db.query(func.count(FormSubmission.id)).filter(
                FormSubmission.user_id == user_id,
                FormSubmission.created_at >= start_date,
                FormSubmission.is_deleted == False
            ).scalar()
            
            # Get submissions by status
            status_counts = db.query(
                FormSubmission.status,
                func.count(FormSubmission.id)
            ).filter(
                FormSubmission.user_id == user_id,
                FormSubmission.created_at >= start_date,
                FormSubmission.is_deleted == False
            ).group_by(FormSubmission.status).all()
            
            # Get average processing time
            avg_processing_time = db.query(
                func.avg(FormSubmission.processing_duration_ms)
            ).filter(
                FormSubmission.user_id == user_id,
                FormSubmission.created_at >= start_date,
                FormSubmission.is_deleted == False,
                FormSubmission.processing_duration_ms.isnot(None)
            ).scalar()
            
            # Get error counts by category
            error_counts = db.query(
                FormSubmission.error_category,
                func.count(FormSubmission.id)
            ).filter(
                FormSubmission.user_id == user_id,
                FormSubmission.created_at >= start_date,
                FormSubmission.is_deleted == False,
                FormSubmission.error_category.isnot(None)
            ).group_by(FormSubmission.error_category).all()
            
            # Get retry metrics
            retry_metrics = db.query(
                func.avg(FormSubmission.retry_count),
                func.max(FormSubmission.retry_count)
            ).filter(
                FormSubmission.user_id == user_id,
                FormSubmission.created_at >= start_date,
                FormSubmission.is_deleted == False
            ).first()
            
            return {
                'total_submissions': total_submissions,
                'status_counts': dict(status_counts),
                'avg_processing_time_ms': avg_processing_time,
                'error_counts': dict(error_counts),
                'retry_metrics': {
                    'avg_retries': retry_metrics[0],
                    'max_retries': retry_metrics[1]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting submission metrics: {str(e)}")
            return {}
    
    def get_submission_timeline(self, user_id: str, days: int = 30) -> List[Dict]:
        """
        Get submission timeline for a user
        
        Args:
            user_id: The user ID to get timeline for
            days: Number of days to look back
            
        Returns:
            List of submission events
        """
        try:
            db = get_db()
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get submissions with events
            submissions = db.query(FormSubmission).filter(
                FormSubmission.user_id == user_id,
                FormSubmission.created_at >= start_date,
                FormSubmission.is_deleted == False
            ).order_by(FormSubmission.created_at.desc()).all()
            
            timeline = []
            for submission in submissions:
                # Add creation event
                timeline.append({
                    'timestamp': submission.created_at,
                    'type': 'submission_created',
                    'submission_id': submission.id,
                    'status': submission.status
                })
                
                # Add status change events
                for event in submission.events:
                    if event['type'] == 'status_changed':
                        timeline.append({
                            'timestamp': datetime.fromisoformat(event['timestamp']),
                            'type': 'status_changed',
                            'submission_id': submission.id,
                            'old_status': event['data']['old_status'],
                            'new_status': event['data']['new_status']
                        })
                
                # Add completion event if completed
                if submission.processing_completed_at:
                    timeline.append({
                        'timestamp': submission.processing_completed_at,
                        'type': 'submission_completed',
                        'submission_id': submission.id,
                        'status': submission.status,
                        'duration_ms': submission.processing_duration_ms
                    })
            
            # Sort timeline by timestamp
            timeline.sort(key=lambda x: x['timestamp'], reverse=True)
            return timeline
            
        except Exception as e:
            logger.error(f"Error getting submission timeline: {str(e)}")
            return []
    
    def get_error_analytics(self, user_id: str, days: int = 30) -> Dict:
        """
        Get error analytics for a user
        
        Args:
            user_id: The user ID to get error analytics for
            days: Number of days to look back
            
        Returns:
            Dict containing error analytics
        """
        try:
            db = get_db()
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get error details
            errors = db.query(FormSubmission).filter(
                FormSubmission.user_id == user_id,
                FormSubmission.created_at >= start_date,
                FormSubmission.is_deleted == False,
                FormSubmission.error_category.isnot(None)
            ).order_by(FormSubmission.created_at.desc()).all()
            
            error_details = []
            for error in errors:
                error_details.append({
                    'timestamp': error.created_at,
                    'submission_id': error.id,
                    'category': error.error_category,
                    'code': error.error_code,
                    'message': error.error_message,
                    'details': error.error_details
                })
            
            # Get error trends
            error_trends = db.query(
                FormSubmission.error_category,
                func.date_trunc('day', FormSubmission.created_at),
                func.count(FormSubmission.id)
            ).filter(
                FormSubmission.user_id == user_id,
                FormSubmission.created_at >= start_date,
                FormSubmission.is_deleted == False,
                FormSubmission.error_category.isnot(None)
            ).group_by(
                FormSubmission.error_category,
                func.date_trunc('day', FormSubmission.created_at)
            ).order_by(
                func.date_trunc('day', FormSubmission.created_at).desc()
            ).all()
            
            return {
                'error_details': error_details,
                'error_trends': [
                    {
                        'date': trend[1].date(),
                        'category': trend[0],
                        'count': trend[2]
                    }
                    for trend in error_trends
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting error analytics: {str(e)}")
            return {} 