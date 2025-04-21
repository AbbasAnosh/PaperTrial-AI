"""
Token models for authentication.
"""

from pydantic import BaseModel

class Token(BaseModel):
    """Token model for authentication responses."""
    access_token: str
    token_type: str 