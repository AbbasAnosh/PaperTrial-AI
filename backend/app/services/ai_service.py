from typing import Dict, List, Any
import openai
from app.core.config import settings

class AIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = "gpt-4-turbo-preview"

    async def analyze_form_fields(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze form elements and suggest field mappings"""
        prompt = f"""
        Analyze these form elements and suggest appropriate field mappings:
        {elements}
        
        Return a JSON object with:
        - field_mappings: List of suggested field names and types
        - confidence_scores: Confidence level for each mapping
        - suggested_validation: Validation rules for each field
        """
        
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content

    async def suggest_field_values(self, field_name: str, context: Dict[str, Any]) -> List[str]:
        """Suggest possible values for a form field based on context"""
        prompt = f"""
        Suggest possible values for the field '{field_name}' based on this context:
        {context}
        
        Return a list of 5 most likely values.
        """
        
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content

    async def generate_form_filling_instructions(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate step-by-step instructions for form filling"""
        prompt = f"""
        Generate detailed instructions for filling this form:
        {form_data}
        
        Include:
        - Required fields
        - Field validation rules
        - Suggested values
        - Common mistakes to avoid
        """
        
        response = await openai.ChatCompletion.acreate(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        
        return response.choices[0].message.content 