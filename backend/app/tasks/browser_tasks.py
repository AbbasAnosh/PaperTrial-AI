from app.core.celery_app import celery_app
from app.services.browser_automation import BrowserAutomation
from app.core.errors import ProcessingError
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def fill_form_task(self, form_data: dict, url: str, user_id: str):
    """
    Fill and submit a web form in the background
    """
    try:
        browser = BrowserAutomation()
        
        # Navigate to form
        browser.navigate(url)
        
        # Fill form fields
        browser.fill_form(form_data)
        
        # Submit form
        result = browser.submit_form()
        
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        logger.error(f"Error filling form: {str(e)}")
        self.retry(exc=e, countdown=30)  # Retry after 30 seconds

@celery_app.task(bind=True)
def analyze_web_form_task(self, url: str, user_id: str):
    """
    Analyze a web form structure
    """
    try:
        browser = BrowserAutomation()
        
        # Navigate to form
        browser.navigate(url)
        
        # Analyze form structure
        structure = browser.analyze_form()
        
        return {
            "status": "success",
            "structure": structure
        }
    except Exception as e:
        logger.error(f"Error analyzing web form: {str(e)}")
        raise ProcessingError("Failed to analyze web form") 