"""
API Examples, Data Models, and Webhook Documentation

This module contains comprehensive examples and documentation for the API,
including interactive examples, data models, and webhook information.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, HttpUrl, constr

# Data Models Documentation
class UserModel(BaseModel):
    """
    User data model.
    
    This model represents a user in the system with all their properties
    and validation rules.
    
    Attributes:
        id (str): Unique identifier for the user
        email (EmailStr): User's email address (must be valid email format)
        full_name (str): User's full name (2-100 characters)
        is_active (bool): Whether the user account is active
        is_admin (bool): Whether the user has administrative privileges
        created_at (datetime): When the user was created
        updated_at (datetime): When the user was last updated
        
    Example:
        ```python
        user = UserModel(
            id="user_123",
            email="user@example.com",
            full_name="John Doe",
            is_active=True,
            is_admin=False,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        ```
    """
    id: str = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="User's email address")
    full_name: constr(min_length=2, max_length=100) = Field(..., description="User's full name")
    is_active: bool = Field(True, description="Whether the user account is active")
    is_admin: bool = Field(False, description="Whether the user has administrative privileges")
    created_at: datetime = Field(..., description="When the user was created")
    updated_at: datetime = Field(..., description="When the user was last updated")

class FormTemplateModel(BaseModel):
    """
    Form template data model.
    
    This model represents a form template with its fields and validation rules.
    
    Attributes:
        id (str): Unique identifier for the template
        name (str): Template name (2-100 characters)
        description (Optional[str]): Template description (max 500 characters)
        fields (List[FormField]): List of form fields
        is_active (bool): Whether the template is active
        created_at (datetime): When the template was created
        updated_at (datetime): When the template was last updated
        
    Example:
        ```python
        template = FormTemplateModel(
            id="template_123",
            name="Invoice Form",
            description="Standard invoice form template",
            fields=[
                FormField(
                    name="invoice_number",
                    type="string",
                    required=True,
                    label="Invoice Number"
                )
            ],
            is_active=True,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        ```
    """
    id: str = Field(..., description="Unique identifier for the template")
    name: constr(min_length=2, max_length=100) = Field(..., description="Template name")
    description: Optional[constr(max_length=500)] = Field(None, description="Template description")
    fields: List["FormField"] = Field(..., description="List of form fields")
    is_active: bool = Field(True, description="Whether the template is active")
    created_at: datetime = Field(..., description="When the template was created")
    updated_at: datetime = Field(..., description="When the template was last updated")

class FormField(BaseModel):
    """
    Form field data model.
    
    This model represents a field in a form template.
    
    Attributes:
        name (str): Field name (must be valid Python identifier)
        type (str): Field type (string, number, date, etc.)
        required (bool): Whether the field is required
        label (str): Human-readable field label
        description (Optional[str]): Field description
        validation (Optional[Dict]): Validation rules
        
    Example:
        ```python
        field = FormField(
            name="invoice_number",
            type="string",
            required=True,
            label="Invoice Number",
            description="Unique invoice identifier",
            validation={
                "pattern": "^INV-\\d{6}$",
                "min_length": 8,
                "max_length": 12
            }
        )
        ```
    """
    name: constr(regex="^[a-zA-Z_][a-zA-Z0-9_]*$") = Field(..., description="Field name")
    type: str = Field(..., description="Field type")
    required: bool = Field(False, description="Whether the field is required")
    label: str = Field(..., description="Human-readable field label")
    description: Optional[str] = Field(None, description="Field description")
    validation: Optional[Dict[str, Any]] = Field(None, description="Validation rules")

# Interactive Examples
API_EXAMPLES = {
    "auth": {
        "login": {
            "description": "Authenticate user and get JWT token",
            "curl": """
curl -X POST "https://api.example.com/api/v1/auth/login" \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "username=user@example.com&password=secretpassword"
            """,
            "python": """
import requests

response = requests.post(
    "https://api.example.com/api/v1/auth/login",
    data={
        "username": "user@example.com",
        "password": "secretpassword"
    }
)
token = response.json()["access_token"]
            """,
            "javascript": """
const response = await fetch("https://api.example.com/api/v1/auth/login", {
    method: "POST",
    headers: {
        "Content-Type": "application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
        username: "user@example.com",
        password: "secretpassword"
    })
});
const { access_token } = await response.json();
            """
        },
        "register": {
            "description": "Register a new user",
            "curl": """
curl -X POST "https://api.example.com/api/v1/auth/register" \\
     -H "Content-Type: application/json" \\
     -d '{
         "email": "user@example.com",
         "password": "secretpassword",
         "full_name": "John Doe"
     }'
            """,
            "python": """
import requests

response = requests.post(
    "https://api.example.com/api/v1/auth/register",
    json={
        "email": "user@example.com",
        "password": "secretpassword",
        "full_name": "John Doe"
    }
)
token = response.json()["access_token"]
            """,
            "javascript": """
const response = await fetch("https://api.example.com/api/v1/auth/register", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        email: "user@example.com",
        password: "secretpassword",
        full_name: "John Doe"
    })
});
const { access_token } = await response.json();
            """
        }
    },
    "forms": {
        "create_template": {
            "description": "Create a new form template",
            "curl": """
curl -X POST "https://api.example.com/api/v1/forms/templates" \\
     -H "Authorization: Bearer {token}" \\
     -H "Content-Type: application/json" \\
     -d '{
         "name": "Invoice Form",
         "description": "Standard invoice form",
         "fields": [
             {
                 "name": "invoice_number",
                 "type": "string",
                 "required": true,
                 "label": "Invoice Number",
                 "validation": {
                     "pattern": "^INV-\\\\d{6}$"
                 }
             }
         ]
     }'
            """,
            "python": """
import requests

response = requests.post(
    "https://api.example.com/api/v1/forms/templates",
    headers={
        "Authorization": f"Bearer {token}"
    },
    json={
        "name": "Invoice Form",
        "description": "Standard invoice form",
        "fields": [
            {
                "name": "invoice_number",
                "type": "string",
                "required": True,
                "label": "Invoice Number",
                "validation": {
                    "pattern": "^INV-\\d{6}$"
                }
            }
        ]
    }
)
template = response.json()
            """,
            "javascript": """
const response = await fetch("https://api.example.com/api/v1/forms/templates", {
    method: "POST",
    headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        name: "Invoice Form",
        description: "Standard invoice form",
        fields: [
            {
                name: "invoice_number",
                type: "string",
                required: true,
                label: "Invoice Number",
                validation: {
                    pattern: "^INV-\\d{6}$"
                }
            }
        ]
    })
});
const template = await response.json();
            """
        },
        "process_pdf": {
            "description": "Process a PDF document",
            "curl": """
curl -X POST "https://api.example.com/api/v1/forms/process-pdf" \\
     -H "Authorization: Bearer {token}" \\
     -F "file=@document.pdf"
            """,
            "python": """
import requests

with open("document.pdf", "rb") as f:
    response = requests.post(
        "https://api.example.com/api/v1/forms/process-pdf",
        headers={
            "Authorization": f"Bearer {token}"
        },
        files={
            "file": ("document.pdf", f, "application/pdf")
        }
    )
result = response.json()
            """,
            "javascript": """
const formData = new FormData();
formData.append("file", document.querySelector("#fileInput").files[0]);

const response = await fetch("https://api.example.com/api/v1/forms/process-pdf", {
    method: "POST",
    headers: {
        "Authorization": `Bearer ${token}`
    },
    body: formData
});
const result = await response.json();
            """
        }
    }
}

# Webhook Documentation
WEBHOOK_DOCS = {
    "events": {
        "form.submitted": {
            "description": "Triggered when a form is submitted",
            "payload": {
                "event": "form.submitted",
                "timestamp": "2024-01-01T00:00:00Z",
                "data": {
                    "submission_id": "sub_123",
                    "template_id": "template_123",
                    "user_id": "user_123",
                    "status": "submitted",
                    "fields": {
                        "invoice_number": "INV-123456",
                        "amount": 1000.00
                    }
                }
            }
        },
        "form.processed": {
            "description": "Triggered when a form submission is processed",
            "payload": {
                "event": "form.processed",
                "timestamp": "2024-01-01T00:00:00Z",
                "data": {
                    "submission_id": "sub_123",
                    "template_id": "template_123",
                    "user_id": "user_123",
                    "status": "processed",
                    "results": {
                        "confidence": 0.95,
                        "extracted_fields": {
                            "invoice_number": "INV-123456",
                            "amount": 1000.00
                        }
                    }
                }
            }
        }
    },
    "security": {
        "description": "Webhooks are secured using HMAC signatures",
        "headers": {
            "X-Webhook-Signature": "HMAC SHA-256 signature of the payload",
            "X-Webhook-Timestamp": "Unix timestamp of the event"
        },
        "verification": """
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
        """
    },
    "retry_policy": {
        "description": "Failed webhook deliveries are retried with exponential backoff",
        "retries": 3,
        "intervals": [5, 30, 300],  # seconds
        "timeout": 10  # seconds
    }
} 