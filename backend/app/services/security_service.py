import hmac
import hashlib
import time
import logging
from typing import Dict, Optional, Tuple
from redis import Redis
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class SecurityService:
    """Service for handling API key authentication and request signing"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.api_key_prefix = "api_key:"
        self.ip_blacklist_prefix = "ip_blacklist:"
        self.signature_prefix = "signature:"
        
    def _get_api_key_key(self, api_key: str) -> str:
        """Generate Redis key for API key"""
        return f"{self.api_key_prefix}{api_key}"
        
    def _get_ip_blacklist_key(self, ip: str) -> str:
        """Generate Redis key for IP blacklist"""
        return f"{self.ip_blacklist_prefix}{ip}"
        
    def _get_signature_key(self, signature: str) -> str:
        """Generate Redis key for request signature"""
        return f"{self.signature_prefix}{signature}"
        
    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an API key
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            if not api_key:
                return False, "API key is required"
                
            # Check if key exists and is active
            key_data = self.redis.hgetall(self._get_api_key_key(api_key))
            if not key_data:
                return False, "Invalid API key"
                
            # Check if key is expired
            expires_at = key_data.get(b'expires_at')
            if expires_at and datetime.fromisoformat(expires_at.decode()) < datetime.utcnow():
                return False, "API key has expired"
                
            # Check if key is revoked
            if key_data.get(b'revoked') == b'1':
                return False, "API key has been revoked"
                
            # Update last used timestamp
            self.redis.hset(
                self._get_api_key_key(api_key),
                'last_used',
                datetime.utcnow().isoformat()
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return False, "Internal server error"
            
    def create_api_key(self, user_id: str, expires_in_days: int = 365) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a new API key
        
        Args:
            user_id: The user ID to associate with the key
            expires_in_days: Number of days until the key expires
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (success, api_key, error_message)
        """
        try:
            # Generate API key
            api_key = hashlib.sha256(f"{user_id}:{time.time()}".encode()).hexdigest()
            
            # Set key data
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            key_data = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': expires_at.isoformat(),
                'revoked': '0',
                'last_used': None
            }
            
            # Store in Redis
            self.redis.hmset(self._get_api_key_key(api_key), key_data)
            self.redis.expire(
                self._get_api_key_key(api_key),
                expires_in_days * 24 * 3600  # Convert days to seconds
            )
            
            return True, api_key, None
            
        except Exception as e:
            logger.error(f"Error creating API key: {str(e)}")
            return False, None, "Internal server error"
            
    def revoke_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        Revoke an API key
        
        Args:
            api_key: The API key to revoke
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            if not self.redis.exists(self._get_api_key_key(api_key)):
                return False, "Invalid API key"
                
            self.redis.hset(self._get_api_key_key(api_key), 'revoked', '1')
            return True, None
            
        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            return False, "Internal server error"
            
    def validate_request_signature(
        self,
        api_key: str,
        timestamp: str,
        signature: str,
        method: str,
        path: str,
        body: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a request signature
        
        Args:
            api_key: The API key used for signing
            timestamp: Request timestamp
            signature: Request signature
            method: HTTP method
            path: Request path
            body: Request body (optional)
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Check if signature was already used (prevent replay attacks)
            if self.redis.exists(self._get_signature_key(signature)):
                return False, "Signature already used"
                
            # Validate timestamp (within 5 minutes)
            try:
                request_time = datetime.fromisoformat(timestamp)
                if abs((datetime.utcnow() - request_time).total_seconds()) > 300:
                    return False, "Request timestamp expired"
            except ValueError:
                return False, "Invalid timestamp format"
                
            # Get API key secret
            key_data = self.redis.hgetall(self._get_api_key_key(api_key))
            if not key_data:
                return False, "Invalid API key"
                
            # Reconstruct signature
            message = f"{method}:{path}:{timestamp}"
            if body:
                message += f":{json.dumps(body, sort_keys=True)}"
                
            expected_signature = hmac.new(
                key_data[b'secret'].encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return False, "Invalid signature"
                
            # Store signature to prevent replay
            self.redis.setex(
                self._get_signature_key(signature),
                300,  # 5 minutes
                '1'
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating request signature: {str(e)}")
            return False, "Internal server error"
            
    def blacklist_ip(self, ip: str, duration_minutes: int = 60) -> bool:
        """
        Blacklist an IP address
        
        Args:
            ip: The IP address to blacklist
            duration_minutes: Duration of blacklist in minutes
            
        Returns:
            bool: Success status
        """
        try:
            self.redis.setex(
                self._get_ip_blacklist_key(ip),
                duration_minutes * 60,
                '1'
            )
            return True
        except Exception as e:
            logger.error(f"Error blacklisting IP: {str(e)}")
            return False
            
    def is_ip_blacklisted(self, ip: str) -> bool:
        """
        Check if an IP is blacklisted
        
        Args:
            ip: The IP address to check
            
        Returns:
            bool: True if blacklisted
        """
        try:
            return bool(self.redis.exists(self._get_ip_blacklist_key(ip)))
        except Exception as e:
            logger.error(f"Error checking IP blacklist: {str(e)}")
            return False 