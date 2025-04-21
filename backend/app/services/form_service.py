"""
Form service for handling form templates and submissions.
"""

import logging
import uuid
import json
import aiohttp
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from bson import ObjectId
from app.models.form_template import (
    FormTemplate, 
    FormTemplateCreate, 
    FormTemplateUpdate,
    FormSubmission,
    FormSubmissionCreate,
    SubmissionMethod
)
from app.core.config import settings
import os
import pandas as pd

logger = logging.getLogger(__name__)

class FormService:
    """Service for handling form templates and submissions."""

    def __init__(self, db):
        """Initialize the form service with database connection."""
        self.db = db
        self.template_collection = db.form_templates
        self.submission_collection = db.form_submissions

    async def get_template_by_id(self, template_id: str) -> Optional[FormTemplate]:
        """Get a form template by ID."""
        try:
            template_dict = await self.template_collection.find_one({"_id": ObjectId(template_id)})
            if template_dict:
                return FormTemplate(**template_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting form template by ID: {str(e)}")
            raise

    async def list_templates(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[FormTemplate]:
        """List form templates with pagination."""
        try:
            query = {"is_active": True} if active_only else {}
            cursor = self.template_collection.find(query).skip(skip).limit(limit)
            templates = []
            async for template_dict in cursor:
                templates.append(FormTemplate(**template_dict))
            return templates
        except Exception as e:
            logger.error(f"Error listing form templates: {str(e)}")
            raise

    async def create_template(self, template_create: FormTemplateCreate, user_id: str) -> FormTemplate:
        """Create a new form template."""
        try:
            template_dict = template_create.dict()
            template_dict["_id"] = ObjectId()
            template_dict["created_by"] = user_id
            template_dict["created_at"] = datetime.utcnow()
            template_dict["is_active"] = True
            template_dict["version"] = 1

            await self.template_collection.insert_one(template_dict)
            return FormTemplate(**template_dict)
        except Exception as e:
            logger.error(f"Error creating form template: {str(e)}")
            raise

    async def update_template(self, template_id: str, template_update: FormTemplateUpdate) -> Optional[FormTemplate]:
        """Update a form template."""
        try:
            update_data = template_update.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            
            # Increment version if fields are updated
            if "fields" in update_data:
                current_template = await self.get_template_by_id(template_id)
                if current_template:
                    update_data["version"] = current_template.version + 1

            result = await self.template_collection.find_one_and_update(
                {"_id": ObjectId(template_id)},
                {"$set": update_data},
                return_document=True
            )
            if result:
                return FormTemplate(**result)
            return None
        except Exception as e:
            logger.error(f"Error updating form template: {str(e)}")
            raise

    async def delete_template(self, template_id: str) -> bool:
        """Delete a form template."""
        try:
            result = await self.template_collection.delete_one({"_id": ObjectId(template_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting form template: {str(e)}")
            raise

    async def create_submission(self, submission_create: FormSubmissionCreate, user_id: str) -> FormSubmission:
        """Create a new form submission."""
        try:
            # Get the template
            template = await self.get_template_by_id(submission_create.template_id)
            if not template:
                raise ValueError(f"Template with ID {submission_create.template_id} not found")

            # Validate submission data against template
            validation_result = await self._validate_submission_data(template, submission_create.data)
            if not validation_result[0]:
                raise ValueError(f"Validation failed: {validation_result[1]}")

            # Create submission record
            submission_dict = submission_create.dict()
            submission_dict["_id"] = ObjectId()
            submission_dict["created_by"] = user_id
            submission_dict["created_at"] = datetime.utcnow()
            submission_dict["status"] = "pending"

            await self.submission_collection.insert_one(submission_dict)
            
            # Process submission asynchronously
            asyncio.create_task(self._process_submission(submission_dict["_id"], template))
            
            return FormSubmission(**submission_dict)
        except Exception as e:
            logger.error(f"Error creating form submission: {str(e)}")
            raise

    async def get_submission_by_id(self, submission_id: str) -> Optional[FormSubmission]:
        """Get a form submission by ID."""
        try:
            submission_dict = await self.submission_collection.find_one({"_id": ObjectId(submission_id)})
            if submission_dict:
                return FormSubmission(**submission_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting form submission by ID: {str(e)}")
            raise

    async def list_submissions(self, user_id: Optional[str] = None, template_id: Optional[str] = None, 
                              skip: int = 0, limit: int = 100) -> List[FormSubmission]:
        """List form submissions with pagination."""
        try:
            query = {}
            if user_id:
                query["created_by"] = user_id
            if template_id:
                query["template_id"] = template_id
                
            cursor = self.submission_collection.find(query).skip(skip).limit(limit)
            submissions = []
            async for submission_dict in cursor:
                submissions.append(FormSubmission(**submission_dict))
            return submissions
        except Exception as e:
            logger.error(f"Error listing form submissions: {str(e)}")
            raise

    async def _validate_submission_data(self, template: FormTemplate, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate submission data against template fields."""
        try:
            for field in template.fields:
                field_name = field.name
                
                # Check required fields
                if field.required and (field_name not in data or data[field_name] is None or data[field_name] == ""):
                    return False, f"Required field '{field.label}' is missing"
                
                # Skip validation for empty optional fields
                if field_name not in data or data[field_name] is None or data[field_name] == "":
                    continue
                
                # Validate field type
                if not await self._validate_field_type(field, data[field_name]):
                    return False, f"Field '{field.label}' has invalid type"
                
                # Apply custom validation rules
                if field.validation_rules:
                    for rule in field.validation_rules:
                        if not await self._apply_validation_rule(rule, data[field_name]):
                            return False, rule.message
            
            return True, "Validation successful"
        except Exception as e:
            logger.error(f"Error validating submission data: {str(e)}")
            return False, f"Validation error: {str(e)}"

    async def _validate_field_type(self, field: Any, value: Any) -> bool:
        """Validate a field value against its type."""
        try:
            if field.field_type == "text":
                return isinstance(value, str)
            elif field.field_type == "number":
                return isinstance(value, (int, float))
            elif field.field_type == "email":
                return isinstance(value, str) and "@" in value and "." in value
            elif field.field_type == "phone":
                return isinstance(value, str) and any(c.isdigit() for c in value)
            elif field.field_type == "date":
                try:
                    datetime.fromisoformat(value)
                    return True
                except:
                    return False
            elif field.field_type == "checkbox":
                return isinstance(value, bool)
            elif field.field_type == "radio":
                return isinstance(value, str) and any(opt["value"] == value for opt in field.options)
            elif field.field_type == "select":
                return isinstance(value, str) and any(opt["value"] == value for opt in field.options)
            elif field.field_type == "textarea":
                return isinstance(value, str)
            elif field.field_type == "file":
                return isinstance(value, str)  # Assuming file path or ID
            elif field.field_type == "hidden":
                return True  # Hidden fields can have any value
            else:
                return True  # Unknown field type, accept any value
        except Exception as e:
            logger.error(f"Error validating field type: {str(e)}")
            return False

    async def _apply_validation_rule(self, rule: Any, value: Any) -> bool:
        """Apply a validation rule to a field value."""
        try:
            if rule.rule_type == "min_length":
                return len(str(value)) >= rule.value
            elif rule.rule_type == "max_length":
                return len(str(value)) <= rule.value
            elif rule.rule_type == "min_value":
                return float(value) >= float(rule.value)
            elif rule.rule_type == "max_value":
                return float(value) <= float(rule.value)
            elif rule.rule_type == "pattern":
                return bool(re.match(rule.value, str(value)))
            elif rule.rule_type == "custom":
                # Custom validation logic could be implemented here
                return True
            else:
                return True  # Unknown rule type, accept the value
        except Exception as e:
            logger.error(f"Error applying validation rule: {str(e)}")
            return False

    async def _submit_http_post(self, template: FormTemplate, submission: FormSubmission) -> Tuple[bool, Dict[str, Any]]:
        """Submit form data via HTTP POST."""
        try:
            if not template.submission_url:
                raise ValueError("Submission URL is required for HTTP POST method")

            async with aiohttp.ClientSession() as session:
                headers = template.submission_headers or {}
                params = template.submission_params or {}
                
                async with session.post(
                    str(template.submission_url),
                    json=submission.data,
                    headers=headers,
                    params=params
                ) as response:
                    response_data = await response.json()
                    return response.status < 400, response_data
        except Exception as e:
            logger.error(f"Error in HTTP POST submission: {str(e)}")
            return False, {"error": str(e)}

    async def _submit_api(self, template: FormTemplate, submission: FormSubmission) -> Tuple[bool, Dict[str, Any]]:
        """Submit form data via API."""
        try:
            if not template.submission_url:
                raise ValueError("Submission URL is required for API method")

            async with aiohttp.ClientSession() as session:
                headers = template.submission_headers or {}
                params = template.submission_params or {}
                
                # Add authentication if provided
                if template.submission_auth:
                    auth_type = template.submission_auth.get("type", "bearer")
                    if auth_type == "bearer":
                        headers["Authorization"] = f"Bearer {template.submission_auth.get('token')}"
                    elif auth_type == "basic":
                        import base64
                        credentials = f"{template.submission_auth.get('username')}:{template.submission_auth.get('password')}"
                        encoded = base64.b64encode(credentials.encode()).decode()
                        headers["Authorization"] = f"Basic {encoded}"
                
                async with session.post(
                    str(template.submission_url),
                    json=submission.data,
                    headers=headers,
                    params=params
                ) as response:
                    response_data = await response.json()
                    return response.status < 400, response_data
        except Exception as e:
            logger.error(f"Error in API submission: {str(e)}")
            return False, {"error": str(e)}

    async def _submit_email(self, template: FormTemplate, submission: FormSubmission) -> Tuple[bool, Dict[str, Any]]:
        """Submit form data via email."""
        try:
            if not template.submission_email_config:
                raise ValueError("Email configuration is required for email submission method")

            email_config = template.submission_email_config
            smtp_settings = email_config.get("smtp_settings", {})
            email_content = email_config.get("email_template", "")

            # Format email content with submission data
            formatted_content = email_content.format(**submission.data)

            # Create email message
            msg = MIMEMultipart()
            msg["From"] = smtp_settings.get("from_email")
            msg["To"] = smtp_settings.get("to_email")
            msg["Subject"] = email_config.get("subject", "Form Submission")

            # Add body
            msg.attach(MIMEText(formatted_content, "html"))

            # Add attachments if any
            if submission.screenshots:
                for filename, content in submission.screenshots.items():
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {filename}",
                    )
                    msg.attach(part)

            # Send email
            with smtplib.SMTP(smtp_settings.get("host"), smtp_settings.get("port")) as server:
                if smtp_settings.get("use_tls"):
                    server.starttls()
                if smtp_settings.get("username"):
                    server.login(smtp_settings.get("username"), smtp_settings.get("password"))
                server.send_message(msg)

            return True, {"message": "Email sent successfully"}

        except Exception as e:
            logger.error(f"Error in email submission: {str(e)}")
            return False, {"error": str(e)}

    async def _submit_file(self, template: FormTemplate, submission: FormSubmission) -> Tuple[bool, Dict[str, Any]]:
        """Submit form data to a file."""
        try:
            if not template.submission_file_config:
                raise ValueError("File configuration is required for file submission method")

            file_config = template.submission_file_config
            file_path = file_config.get("path")
            file_format = file_config.get("format", "json")

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Format data based on file format
            if file_format == "json":
                content = json.dumps(submission.data, indent=2)
                file_path = f"{file_path}.json"
            elif file_format == "csv":
                content = pd.DataFrame(submission.data).to_csv(index=False)
                file_path = f"{file_path}.csv"
            else:
                raise ValueError(f"Unsupported file format: {file_format}")

            # Write to file
            with open(file_path, "w") as f:
                f.write(content)

            return True, {"file_path": file_path}

        except Exception as e:
            logger.error(f"Error in file submission: {str(e)}")
            return False, {"error": str(e)}

    async def _submit_custom(self, template: FormTemplate, submission: FormSubmission) -> Tuple[bool, Dict[str, Any]]:
        """Submit form data using a custom method."""
        # This would allow for custom submission logic
        # For now, just return a placeholder
        return False, {"error": "Custom submission not implemented"}

    async def _process_submission(self, submission_id: str, template: FormTemplate) -> None:
        """Process a form submission based on the template's submission method."""
        try:
            # Get the submission
            submission = await self.get_submission_by_id(str(submission_id))
            if not submission:
                logger.error(f"Submission with ID {submission_id} not found")
                return

            # Update status to processing and set start time
            await self.submission_collection.update_one(
                {"_id": ObjectId(str(submission_id))},
                {
                    "$set": {
                        "status": "processing",
                        "processing_started_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Process based on submission method
            success = False
            error_message = None
            error_category = None
            error_code = None
            error_details = None
            response_data = None

            try:
                if template.submission_method == SubmissionMethod.HTTP_POST:
                    success, response_data = await self._submit_http_post(template, submission)
                elif template.submission_method == SubmissionMethod.API:
                    success, response_data = await self._submit_api(template, submission)
                elif template.submission_method == SubmissionMethod.EMAIL:
                    success, response_data = await self._submit_email(template, submission)
                elif template.submission_method == SubmissionMethod.FILE:
                    success, response_data = await self._submit_file(template, submission)
                elif template.submission_method == SubmissionMethod.CUSTOM:
                    success, response_data = await self._submit_custom(template, submission)
                else:
                    error_message = f"Unsupported submission method: {template.submission_method}"
                    error_category = "validation"
                    error_code = "UNSUPPORTED_METHOD"
            except aiohttp.ClientError as e:
                error_message = str(e)
                error_category = "network"
                error_code = "NETWORK_ERROR"
                error_details = {"error_type": type(e).__name__}
                logger.error(f"Network error in submission processing: {str(e)}")
            except ValidationError as e:
                error_message = str(e)
                error_category = "validation"
                error_code = "VALIDATION_ERROR"
                error_details = {"errors": e.errors()}
                logger.error(f"Validation error in submission processing: {str(e)}")
            except TimeoutError as e:
                error_message = str(e)
                error_category = "timeout"
                error_code = "TIMEOUT_ERROR"
                logger.error(f"Timeout error in submission processing: {str(e)}")
            except Exception as e:
                error_message = str(e)
                error_category = "system"
                error_code = "SYSTEM_ERROR"
                error_details = {"error_type": type(e).__name__}
                logger.error(f"System error in submission processing: {str(e)}")

            # Update submission status with metrics
            status = "completed" if success else "failed"
            await self.submission_collection.update_one(
                {"_id": ObjectId(str(submission_id))},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow(),
                        "error_message": error_message,
                        "error_category": error_category,
                        "error_code": error_code,
                        "error_details": error_details,
                        "response_data": response_data,
                        "processing_completed_at": datetime.utcnow()
                    }
                }
            )

            # Calculate and update processing duration
            if submission.processing_started_at:
                duration_ms = int((datetime.utcnow() - submission.processing_started_at).total_seconds() * 1000)
                await self.submission_collection.update_one(
                    {"_id": ObjectId(str(submission_id))},
                    {"$set": {"processing_duration_ms": duration_ms}}
                )

        except Exception as e:
            logger.error(f"Error in submission processing: {str(e)}")
            # Update submission status to failed with system error
            await self.submission_collection.update_one(
                {"_id": ObjectId(str(submission_id))},
                {
                    "$set": {
                        "status": "failed",
                        "updated_at": datetime.utcnow(),
                        "error_message": f"Processing error: {str(e)}",
                        "error_category": "system",
                        "error_code": "PROCESSING_ERROR",
                        "error_details": {"error_type": type(e).__name__},
                        "processing_completed_at": datetime.utcnow()
                    }
                }
            ) 