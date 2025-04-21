"""
Service for handling one-click form submissions.
Combines browser automation, AI form filling, and submission tracking.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import asyncio
from app.services.browser_automation import BrowserAutomationService
from app.services.web_form_processor import WebFormProcessor
from app.services.form_agent import FormAgent
from app.services.ai_service import AIService
from app.models.form_submission import FormSubmission
from app.core.config import settings

logger = logging.getLogger(__name__)

class OneClickSubmissionService:
    def __init__(self):
        self.browser_automation = BrowserAutomationService()
        self.web_form_processor = WebFormProcessor()
        self.form_agent = FormAgent()
        self.ai_service = AIService()
        self.screenshot_dir = Path("temp/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def process_submission(
        self,
        form_url: str,
        user_data: Dict[str, Any],
        documents: Dict[str, str],
        form_type: str = "web",  # "web" or "pdf"
        preview_only: bool = False
    ) -> Dict[str, Any]:
        """
        Process a form submission with one-click automation.
        
        Args:
            form_url: URL of the form or path to PDF
            user_data: User data to fill in the form
            documents: Documents to upload
            form_type: Type of form ("web" or "pdf")
            preview_only: If True, only fill the form without submitting
            
        Returns:
            Dict containing submission results
        """
        try:
            # Initialize submission tracking
            submission = FormSubmission(
                form_url=form_url,
                form_type=form_type,
                status="processing",
                user_data=user_data,
                documents=documents,
                created_at=datetime.utcnow()
            )

            # Step 1: Process form structure
            if form_type == "web":
                form_structure = await self.web_form_processor.process_form(form_url)
            else:
                # For PDF forms, use the form agent to process
                form_structure = await self.form_agent.process_form(
                    form_id="pdf_form",
                    user_data=user_data,
                    documents=documents
                )

            # Step 2: AI-powered form filling
            filled_data = await self.ai_service.fill_form(
                form_data=user_data,
                form_structure=form_structure
            )

            # Step 3: Preview and confirmation
            if preview_only:
                submission.status = "preview"
                submission.filled_data = filled_data
                return submission.dict()

            # Step 4: Browser automation for submission
            if form_type == "web":
                # Use browser automation for web forms
                await self.browser_automation.initialize()
                await self.browser_automation.fill_form(form_url, filled_data)
                
                # Take screenshot before submission
                before_screenshot = await self._capture_screenshot("before_submission")
                
                # Submit the form
                submission_result = await self.browser_automation.submit_form()
                
                # Take screenshot after submission
                after_screenshot = await self._capture_screenshot("after_submission")
                
                # Update submission with results
                submission.status = "completed" if submission_result else "failed"
                submission.screenshots = {
                    "before": before_screenshot,
                    "after": after_screenshot
                }
                submission.submission_result = submission_result
            else:
                # For PDF forms, use the form agent
                submission_result = await self.form_agent.process_form(
                    form_id="pdf_form",
                    user_data=filled_data,
                    documents=documents
                )
                
                submission.status = "completed" if submission_result["status"] == "success" else "failed"
                submission.submission_result = submission_result

            # Step 5: Update submission metadata
            submission.updated_at = datetime.utcnow()
            submission.completed_at = datetime.utcnow()
            
            return submission.dict()

        except Exception as e:
            logger.error(f"Error in one-click submission: {str(e)}", exc_info=True)
            if submission:
                submission.status = "failed"
                submission.error = str(e)
                submission.updated_at = datetime.utcnow()
            return {
                "status": "failed",
                "error": str(e)
            }
        finally:
            # Cleanup
            await self.browser_automation.close()
            await self.web_form_processor.cleanup()

    async def _capture_screenshot(self, prefix: str) -> str:
        """Capture a screenshot and return the file path"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            await self.browser_automation.page.screenshot(path=str(filepath))
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {str(e)}")
            return "" 