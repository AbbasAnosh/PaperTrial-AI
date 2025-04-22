import requests
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config.database import get_db
from app.config.redis import get_redis_client
import hmac
import hashlib
import base64

logger = logging.getLogger(__name__)

class WebhookService:
    """Service for managing and sending webhooks"""
    
    def __init__(self):
        self.db = get_db()
        self.redis = get_redis_client()
        
    def register_webhook(self, user_id: str, url: str, events: List[str], secret: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new webhook for a user
        
        Args:
            user_id: The user ID
            url: The webhook URL
            events: List of events to subscribe to
            secret: Optional secret for signing webhooks
            
        Returns:
            Dict with webhook details
        """
        try:
            # Generate a secret if not provided
            if not secret:
                secret = base64.b64encode(os.urandom(32)).decode('utf-8')
                
            # Store webhook in database
            result = self.db.table('webhooks').insert({
                'user_id': user_id,
                'url': url,
                'events': events,
                'secret': secret,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).execute()
            
            if result.data:
                webhook = result.data[0]
                logger.info(f"Registered webhook {webhook['id']} for user {user_id}")
                return {
                    'id': webhook['id'],
                    'url': webhook['url'],
                    'events': webhook['events'],
                    'secret': webhook['secret'],
                    'is_active': webhook['is_active']
                }
            else:
                raise Exception("Failed to register webhook")
                
        except Exception as e:
            logger.error(f"Error registering webhook: {str(e)}")
            raise
            
    def update_webhook(self, webhook_id: str, url: Optional[str] = None, 
                      events: Optional[List[str]] = None, is_active: Optional[bool] = None) -> Dict[str, Any]:
        """
        Update an existing webhook
        
        Args:
            webhook_id: The webhook ID
            url: Optional new URL
            events: Optional new events list
            is_active: Optional active status
            
        Returns:
            Dict with updated webhook details
        """
        try:
            update_data = {}
            if url is not None:
                update_data['url'] = url
            if events is not None:
                update_data['events'] = events
            if is_active is not None:
                update_data['is_active'] = is_active
                
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.db.table('webhooks').update(update_data).eq('id', webhook_id).execute()
            
            if result.data:
                logger.info(f"Updated webhook {webhook_id}")
                return result.data[0]
            else:
                raise Exception(f"Webhook {webhook_id} not found")
                
        except Exception as e:
            logger.error(f"Error updating webhook: {str(e)}")
            raise
            
    def delete_webhook(self, webhook_id: str) -> bool:
        """
        Delete a webhook
        
        Args:
            webhook_id: The webhook ID
            
        Returns:
            bool: True if successful
        """
        try:
            result = self.db.table('webhooks').delete().eq('id', webhook_id).execute()
            
            if result.data:
                logger.info(f"Deleted webhook {webhook_id}")
                return True
            else:
                raise Exception(f"Webhook {webhook_id} not found")
                
        except Exception as e:
            logger.error(f"Error deleting webhook: {str(e)}")
            raise
            
    def get_webhooks(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all webhooks for a user
        
        Args:
            user_id: The user ID
            
        Returns:
            List of webhook details
        """
        try:
            result = self.db.table('webhooks').select('*').eq('user_id', user_id).execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting webhooks: {str(e)}")
            raise
            
    def _sign_payload(self, payload: Dict[str, Any], secret: str) -> str:
        """
        Sign a webhook payload with HMAC
        
        Args:
            payload: The payload to sign
            secret: The secret to use for signing
            
        Returns:
            str: The signature
        """
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
        
    def send_webhook(self, webhook_id: str, event: str, payload: Dict[str, Any]) -> bool:
        """
        Send a webhook
        
        Args:
            webhook_id: The webhook ID
            event: The event type
            payload: The payload to send
            
        Returns:
            bool: True if successful
        """
        try:
            # Get webhook details
            result = self.db.table('webhooks').select('*').eq('id', webhook_id).execute()
            
            if not result.data:
                logger.error(f"Webhook {webhook_id} not found")
                return False
                
            webhook = result.data[0]
            
            # Check if webhook is active
            if not webhook['is_active']:
                logger.info(f"Webhook {webhook_id} is inactive, skipping")
                return False
                
            # Check if webhook is subscribed to this event
            if event not in webhook['events']:
                logger.info(f"Webhook {webhook_id} is not subscribed to event {event}, skipping")
                return False
                
            # Prepare payload
            webhook_payload = {
                'event': event,
                'timestamp': datetime.utcnow().isoformat(),
                'data': payload
            }
            
            # Sign payload if secret exists
            headers = {'Content-Type': 'application/json'}
            if webhook['secret']:
                signature = self._sign_payload(webhook_payload, webhook['secret'])
                headers['X-PaperTrail-Signature'] = signature
                
            # Send webhook
            response = requests.post(
                webhook['url'],
                json=webhook_payload,
                headers=headers,
                timeout=10
            )
            
            # Log result
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Successfully sent webhook {webhook_id} for event {event}")
                return True
            else:
                logger.warning(f"Failed to send webhook {webhook_id} for event {event}: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending webhook: {str(e)}")
            return False
            
    def send_submission_webhook(self, submission_id: str, event: str) -> bool:
        """
        Send a webhook for a submission event
        
        Args:
            submission_id: The submission ID
            event: The event type
            
        Returns:
            bool: True if at least one webhook was sent successfully
        """
        try:
            # Get submission details
            submission_result = self.db.table('form_submissions').select('*').eq('id', submission_id).execute()
            
            if not submission_result.data:
                logger.error(f"Submission {submission_id} not found")
                return False
                
            submission = submission_result.data[0]
            user_id = submission['user_id']
            
            # Get user's webhooks
            webhooks = self.get_webhooks(user_id)
            
            if not webhooks:
                logger.info(f"No webhooks found for user {user_id}")
                return False
                
            # Prepare payload
            payload = {
                'submission_id': submission_id,
                'status': submission['status'],
                'created_at': submission['created_at'],
                'updated_at': submission['updated_at']
            }
            
            # Add event-specific data
            if event == 'submission.created':
                payload['data'] = submission['data']
            elif event == 'submission.updated':
                payload['status'] = submission['status']
                payload['error_category'] = submission.get('error_category')
                payload['error_code'] = submission.get('error_code')
            elif event == 'submission.completed':
                payload['status'] = submission['status']
                payload['processing_duration_ms'] = submission.get('processing_duration_ms')
            elif event == 'submission.failed':
                payload['status'] = submission['status']
                payload['error_category'] = submission.get('error_category')
                payload['error_code'] = submission.get('error_code')
                payload['error_details'] = submission.get('error_details')
                payload['retry_count'] = submission.get('retry_count')
                
            # Send webhooks
            success = False
            for webhook in webhooks:
                if self.send_webhook(webhook['id'], event, payload):
                    success = True
                    
            return success
            
        except Exception as e:
            logger.error(f"Error sending submission webhook: {str(e)}")
            return False 