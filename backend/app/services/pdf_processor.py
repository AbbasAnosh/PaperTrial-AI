from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import convert_to_dict
import asyncio
from typing import Dict, Any, List, Optional
import os
from app.services.ai_service import AIService
from functools import lru_cache
import numpy as np
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import euclidean
import json
import logging
from datetime import datetime, timedelta
import hashlib

class PDFProcessor:
    def __init__(self):
        self.api_key = os.getenv("UNSTRUCTURED_API_KEY")
        if not self.api_key:
            raise ValueError("UNSTRUCTURED_API_KEY environment variable is not set")
        self.ai_service = AIService()
        self.cache_dir = "cache"
        self.cache_ttl = timedelta(hours=24)  # Cache TTL of 24 hours
        os.makedirs(self.cache_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def _get_cache_key(self, file_path: str, form_type: Optional[str] = None) -> str:
        """Generate a unique cache key based on file content and form type"""
        file_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
        return f"{file_hash}_{form_type or 'default'}"

    def _is_cache_valid(self, cache_path: str) -> bool:
        """Check if cache file is still valid based on TTL"""
        if not os.path.exists(cache_path):
            return False
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - cache_time < self.cache_ttl

    @lru_cache(maxsize=100)
    async def process_pdf(self, file_path: str, form_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a PDF file and extract its content using Unstructured.io
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(file_path, form_type)
            cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
            
            if os.path.exists(cache_path) and self._is_cache_valid(cache_path):
                self.logger.info(f"Using cached results for {file_path}")
                with open(cache_path, 'r') as f:
                    return json.load(f)

            self.logger.info(f"Processing PDF: {file_path}")
            start_time = datetime.now()

            # Process PDF using Unstructured.io with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    elements = partition_pdf(
                        filename=file_path,
                        strategy="hi_res",
                        api_key=self.api_key
                    )
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    self.logger.warning(f"Retry {attempt + 1} after error: {str(e)}")
                    await asyncio.sleep(1)

            # Convert elements to dictionary format
            pdf_data = convert_to_dict(elements)

            # Extract form fields using AI with timeout
            try:
                form_fields = await asyncio.wait_for(
                    self._extract_form_fields(pdf_data),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                self.logger.error("Form field extraction timed out")
                form_fields = []
            
            # Cluster related fields
            clustered_fields = self._cluster_fields(form_fields)
            
            # Generate field suggestions with timeout
            try:
                field_suggestions = await asyncio.wait_for(
                    self._generate_field_suggestions(clustered_fields),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                self.logger.error("Field suggestions generation timed out")
                field_suggestions = {}

            # Process the data
            processed_data = {
                "elements": pdf_data,
                "form_fields": clustered_fields,
                "field_suggestions": field_suggestions,
                "metadata": {
                    "page_count": len(set(e.page_number for e in elements if hasattr(e, 'page_number'))),
                    "text_blocks": len([e for e in elements if e.category == "Text"]),
                    "form_type": form_type,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "file_size": os.path.getsize(file_path),
                    "processed_at": datetime.now().isoformat()
                }
            }

            # Cache the results
            with open(cache_path, 'w') as f:
                json.dump(processed_data, f)

            self.logger.info(f"Successfully processed PDF in {(datetime.now() - start_time).total_seconds():.2f} seconds")
            return processed_data

        except Exception as e:
            self.logger.error(f"Failed to process PDF: {str(e)}", exc_info=True)
            if isinstance(e, ValueError) and "Please sign in" in str(e):
                raise ValueError("Authentication error. Please sign in to proceed.")
            else:
                raise Exception(f"Failed to process PDF: {str(e)}")

    async def _extract_form_fields(self, pdf_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract form fields using AI analysis with confidence scores"""
        try:
            response = await self.ai_service.analyze_form_fields(pdf_data)
            
            # Add confidence scores if not present
            for field in response:
                if "confidence_score" not in field:
                    field["confidence_score"] = self._calculate_confidence_score(field)
            
            return response
        except Exception as e:
            self.logger.error(f"Error extracting form fields: {str(e)}", exc_info=True)
            return []

    def _cluster_fields(self, form_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cluster related form fields based on position and content"""
        if not form_fields:
            return []

        try:
            # Extract field positions
            positions = np.array([[f["position"]["x"], f["position"]["y"]] for f in form_fields])
            
            # Perform DBSCAN clustering with adaptive parameters
            eps = min(50, max(10, np.mean([euclidean(p1, p2) for p1 in positions for p2 in positions]) / 2))
            min_samples = max(2, len(positions) // 10)
            
            clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(positions)
            
            # Add cluster information to fields
            for i, field in enumerate(form_fields):
                field["cluster"] = int(clustering.labels_[i])
                
                # Find related fields in the same cluster
                if clustering.labels_[i] != -1:
                    related_indices = np.where(clustering.labels_ == clustering.labels_[i])[0]
                    field["related_fields"] = [form_fields[j]["field_name"] for j in related_indices if j != i]
            
            return form_fields
        except Exception as e:
            self.logger.error(f"Error clustering fields: {str(e)}", exc_info=True)
            return form_fields

    def _calculate_confidence_score(self, field: Dict[str, Any]) -> float:
        """Calculate confidence score based on field attributes"""
        try:
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
        except Exception as e:
            self.logger.error(f"Error calculating confidence score: {str(e)}", exc_info=True)
            return 0.5

    async def _generate_field_suggestions(self, form_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Generate smart suggestions for form fields"""
        suggestions = {}
        for field in form_fields:
            try:
                context = {
                    "field_name": field["field_name"],
                    "field_type": field["field_type"],
                    "previous_values": field.get("field_value", [])
                }
                suggestions[field["field_name"]] = await self.ai_service.suggest_field_values(
                    field["field_name"],
                    context
                )
            except Exception as e:
                self.logger.error(f"Error generating suggestions for field {field.get('field_name')}: {str(e)}", exc_info=True)
                suggestions[field["field_name"]] = []
        return suggestions

    def cleanup(self, file_path: str):
        """Clean up temporary files and old cache entries"""
        try:
            # Remove the processed file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Clean up old cache entries
            for cache_file in os.listdir(self.cache_dir):
                cache_path = os.path.join(self.cache_dir, cache_file)
                if not self._is_cache_valid(cache_path):
                    os.remove(cache_path)
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}", exc_info=True) 