"""
Enhanced form service with improved error handling and retry logic.
This file contains the enhanced version of the form service that can be manually integrated.
"""

import logging
import traceback
from datetime import datetime, timedelta
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import json
import pandas as pd

from app.models.form_submission import FormSubmission
from app.models.form_template import FormTemplate

logger = logging.getLogger(__name__)

class EnhancedFormService:
    """
    Enhanced form service with improved error handling and retry logic.
    """
    
    def _categorize_error(self, exception):
        """
        Categorize an exception into an error category.
        
        Args:
            exception: The exception to categorize
            
        Returns:
            str: The error category
        """
        if isinstance(exception, requests.exceptions.RequestException):
            return "network"
        elif isinstance(exception, ValueError):
            return "validation"
        elif isinstance(exception, TimeoutError):
            return "timeout"
        elif isinstance(exception, Exception):
            return "system"
        else:
            return "unknown"
    
    def _submit_email(self, form_template, submission):
        """
        Submit form data via email.
        
        Args:
            form_template: The form template
            submission: The form submission
            
        Returns:
            dict: The result of the submission
        """
        # Check if email configuration is provided
        if not form_template.submission_config or 'email' not in form_template.submission_config:
            raise ValueError("Email configuration is missing")
        
        email_config = form_template.submission_config['email']
        required_fields = ['to', 'subject', 'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password']
        
        for field in required_fields:
            if field not in email_config:
                raise ValueError(f"Email configuration is missing required field: {field}")
        
        # Format email content
        content = f"Form Submission: {form_template.name}\n\n"
        for field in form_template.fields:
            field_value = submission.data.get(field.name, '')
            content += f"{field.label}: {field_value}\n"
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = email_config.get('from', email_config['smtp_username'])
        msg['To'] = email_config['to']
        msg['Subject'] = email_config['subject']
        
        # Add body
        msg.attach(MIMEText(content, 'plain'))
        
        # Add attachments if any
        if 'attachments' in submission.data:
            for attachment in submission.data['attachments']:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {attachment['filename']}")
                msg.attach(part)
        
        # Send email
        try:
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['smtp_username'], email_config['smtp_password'])
            server.send_message(msg)
            server.quit()
            
            return {
                'status': 'success',
                'message': 'Email sent successfully',
                'recipient': email_config['to']
            }
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise
    
    def _submit_file(self, form_template, submission):
        """
        Submit form data to a file.
        
        Args:
            form_template: The form template
            submission: The form submission
            
        Returns:
            dict: The result of the submission
        """
        # Check if file configuration is provided
        if not form_template.submission_config or 'file' not in form_template.submission_config:
            raise ValueError("File configuration is missing")
        
        file_config = form_template.submission_config['file']
        required_fields = ['directory', 'filename', 'format']
        
        for field in required_fields:
            if field not in file_config:
                raise ValueError(f"File configuration is missing required field: {field}")
        
        # Create directory if it doesn't exist
        os.makedirs(file_config['directory'], exist_ok=True)
        
        # Format data based on file format
        if file_config['format'] == 'json':
            data = submission.data
            file_path = os.path.join(file_config['directory'], file_config['filename'])
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        elif file_config['format'] == 'csv':
            data = []
            for field in form_template.fields:
                data.append({
                    'field': field.label,
                    'value': submission.data.get(field.name, '')
                })
            df = pd.DataFrame(data)
            file_path = os.path.join(file_config['directory'], file_config['filename'])
            df.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported file format: {file_config['format']}")
        
        return {
            'status': 'success',
            'message': 'Data written to file successfully',
            'file_path': file_path
        }
    
    def _process_submission(self, submission_id):
        """
        Process a form submission based on the template's submission method.
        
        Args:
            submission_id: UUID of the form submission to process
            
        Returns:
            dict: The result of the submission
        """
        # Get the submission
        submission = FormSubmission.get(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Get the form template
        form_template = FormTemplate.get(submission.form_template_id)
        if not form_template:
            raise ValueError(f"Form template {submission.form_template_id} not found")
        
        # Update submission status to processing
        submission.status = "processing"
        submission.processing_started_at = datetime.utcnow()
        submission.save()
        
        try:
            # Process the submission based on the template's submission method
            if form_template.submission_method == "HTTP_POST":
                result = self._submit_http_post(form_template, submission)
            elif form_template.submission_method == "API":
                result = self._submit_api(form_template, submission)
            elif form_template.submission_method == "EMAIL":
                result = self._submit_email(form_template, submission)
            elif form_template.submission_method == "FILE":
                result = self._submit_file(form_template, submission)
            elif form_template.submission_method == "CUSTOM":
                result = self._submit_custom(form_template, submission)
            else:
                raise ValueError(f"Unknown submission method: {form_template.submission_method}")
            
            # Update submission status to completed
            submission.status = "completed"
            submission.processing_completed_at = datetime.utcnow()
            submission.processing_duration_ms = int((submission.processing_completed_at - submission.processing_started_at).total_seconds() * 1000)
            submission.response_data = result
            submission.save()
            
            return result
            
        except Exception as e:
            # Log the error
            logger.error(f"Error processing submission {submission_id}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Categorize the error
            error_category = self._categorize_error(e)
            
            # Update submission status to failed
            submission.status = "failed"
            submission.processing_completed_at = datetime.utcnow()
            submission.processing_duration_ms = int((submission.processing_completed_at - submission.processing_started_at).total_seconds() * 1000)
            submission.error_message = str(e)
            submission.error_category = error_category
            submission.error_details = {
                "exception": str(e),
                "traceback": traceback.format_exc()
            }
            
            # Calculate next retry time with exponential backoff
            if submission.retry_count < submission.max_retries:
                backoff_seconds = submission.retry_backoff_seconds * (2 ** submission.retry_count)
                submission.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            
            submission.save()
            
            # Re-raise the exception
            raise
    
    def update_submission_status(self, submission_id, new_status, error_message=None, 
                                error_category=None, error_code=None, error_details=None, 
                                response_data=None):
        """
        Update a submission's status and related fields.
        
        Args:
            submission_id: UUID of the submission to update
            new_status: The new status
            error_message: Error message (if any)
            error_category: Error category (if any)
            error_code: Error code (if any)
            error_details: Error details (if any)
            response_data: Response data (if any)
            
        Returns:
            FormSubmission: The updated submission
        """
        # Get the submission
        submission = FormSubmission.get(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Update the submission
        submission.status = new_status
        
        if error_message:
            submission.error_message = error_message
        
        if error_category:
            submission.error_category = error_category
        
        if error_code:
            submission.error_code = error_code
        
        if error_details:
            submission.error_details = error_details
        
        if response_data:
            submission.response_data = response_data
        
        # Update processing metrics if status is completed or failed
        if new_status in ["completed", "failed", "cancelled"] and submission.processing_started_at:
            submission.processing_completed_at = datetime.utcnow()
            submission.processing_duration_ms = int((submission.processing_completed_at - submission.processing_started_at).total_seconds() * 1000)
        
        # Calculate next retry time if status is failed
        if new_status == "failed" and submission.retry_count < submission.max_retries:
            backoff_seconds = submission.retry_backoff_seconds * (2 ** submission.retry_count)
            submission.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
        
        submission.save()
        
        return submission 