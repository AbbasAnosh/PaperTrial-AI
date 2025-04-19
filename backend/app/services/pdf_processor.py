from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import convert_to_dict
import asyncio
from typing import Dict, Any, List
import os
from app.services.ai_service import AIService
from functools import lru_cache
import numpy as np
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import euclidean
import json

class PDFProcessor:
    def __init__(self):
        self.api_key = os.getenv("UNSTRUCTURED_API_KEY")
        if not self.api_key:
            raise ValueError("UNSTRUCTURED_API_KEY environment variable is not set")
        self.ai_service = AIService()
        self.cache_dir = "cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    @lru_cache(maxsize=100)
    async def process_pdf(self, file_path: str, form_type: str = None) -> Dict[str, Any]:
        """
        Process a PDF file and extract its content using Unstructured.io
        """
        try:
            # Check cache first
            cache_key = f"{os.path.basename(file_path)}_{form_type}"
            cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
            
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    return json.load(f)

            # Process PDF using Unstructured.io
            elements = partition_pdf(
                filename=file_path,
                strategy="hi_res",
                api_key=self.api_key
            )

            # Convert elements to dictionary format
            pdf_data = convert_to_dict(elements)

            # Extract form fields using AI
            form_fields = await self._extract_form_fields(pdf_data)
            
            # Cluster related fields
            clustered_fields = self._cluster_fields(form_fields)
            
            # Generate field suggestions
            field_suggestions = await self._generate_field_suggestions(clustered_fields)

            # Process the data
            processed_data = {
                "elements": pdf_data,
                "form_fields": clustered_fields,
                "field_suggestions": field_suggestions,
                "metadata": {
                    "page_count": len(set(e.page_number for e in elements if hasattr(e, 'page_number'))),
                    "text_blocks": len([e for e in elements if e.category == "Text"]),
                    "form_type": form_type
                }
            }

            # Cache the results
            with open(cache_path, 'w') as f:
                json.dump(processed_data, f)

            return processed_data

        except Exception as e:
            raise Exception(f"Failed to process PDF: {str(e)}")

    async def _extract_form_fields(self, pdf_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract form fields using AI analysis with confidence scores"""
        prompt = f"""
        Analyze this PDF content and extract form fields:
        {pdf_data}
        
        Return a JSON object with:
        - field_name: The name of the field
        - field_type: The type of field (text, checkbox, radio, etc.)
        - field_value: Any pre-filled values
        - is_required: Whether the field is required
        - validation_rules: Any validation rules found
        - confidence_score: A score between 0 and 1 indicating extraction confidence
        - position: The field's position on the page
        """
        
        response = await self.ai_service.analyze_form_fields(pdf_data)
        
        # Add confidence scores if not present
        for field in response:
            if "confidence_score" not in field:
                field["confidence_score"] = self._calculate_confidence_score(field)
        
        return response

    def _cluster_fields(self, form_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cluster related form fields based on position and content"""
        # Extract field positions
        positions = np.array([[f["position"]["x"], f["position"]["y"]] for f in form_fields])
        
        # Perform DBSCAN clustering
        clustering = DBSCAN(eps=50, min_samples=2).fit(positions)
        
        # Add cluster information to fields
        for i, field in enumerate(form_fields):
            field["cluster"] = int(clustering.labels_[i])
            
            # Find related fields in the same cluster
            if clustering.labels_[i] != -1:
                related_indices = np.where(clustering.labels_ == clustering.labels_[i])[0]
                field["related_fields"] = [form_fields[j]["field_name"] for j in related_indices if j != i]
        
        return form_fields

    def _calculate_confidence_score(self, field: Dict[str, Any]) -> float:
        """Calculate confidence score based on field attributes"""
        score = 1.0
        
        # Reduce score for missing attributes
        if not field.get("field_name"):
            score *= 0.5
        if not field.get("field_type"):
            score *= 0.7
        if not field.get("validation_rules"):
            score *= 0.9
            
        # Adjust score based on field value presence and quality
        if field.get("field_value"):
            if len(str(field["field_value"])) < 2:
                score *= 0.8
        else:
            score *= 0.6
            
        return round(score, 2)

    async def _generate_field_suggestions(self, form_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Generate smart suggestions for form fields"""
        suggestions = {}
        for field in form_fields:
            context = {
                "field_name": field["field_name"],
                "field_type": field["field_type"],
                "previous_values": field.get("field_value", [])
            }
            suggestions[field["field_name"]] = await self.ai_service.suggest_field_values(
                field["field_name"],
                context
            )
        return suggestions

    def cleanup(self, file_path: str):
        """Clean up temporary files"""
        if os.path.exists(file_path):
            os.remove(file_path) 