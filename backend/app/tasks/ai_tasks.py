from app.core.celery_app import celery_app
from app.services.ai_service import AIService
from app.services.nlp_service import NLPService
from app.core.errors import ProcessingError
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def process_ai_mapping_task(self, form_data: dict, user_id: str):
    """
    Process AI mapping in the background
    """
    try:
        ai_service = AIService()
        nlp_service = NLPService()
        
        # Analyze form fields
        field_analysis = nlp_service.analyze_fields(form_data)
        
        # Generate AI mapping
        mapping = ai_service.generate_mapping(field_analysis)
        
        return {
            "status": "success",
            "mapping": mapping
        }
    except Exception as e:
        logger.error(f"Error processing AI mapping: {str(e)}")
        self.retry(exc=e, countdown=45)  # Retry after 45 seconds

@celery_app.task(bind=True)
def analyze_form_structure_task(self, form_id: str, user_id: str):
    """
    Analyze form structure using AI
    """
    try:
        ai_service = AIService()
        nlp_service = NLPService()
        
        # Get form structure
        structure = nlp_service.get_form_structure(form_id)
        
        # Analyze with AI
        analysis = ai_service.analyze_structure(structure)
        
        return {
            "status": "success",
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Error analyzing form structure: {str(e)}")
        raise ProcessingError("Failed to analyze form structure") 