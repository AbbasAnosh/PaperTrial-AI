"""
Mapping service for handling the mapping between extracted PDF data and form fields.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bson import ObjectId
from app.models.form_template import FormTemplate, FormField
from app.services.pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

class MappingService:
    """Service for handling mapping between extracted PDF data and form fields."""

    def __init__(self, db, pdf_processor: PDFProcessor):
        """Initialize the mapping service with database connection and PDF processor."""
        self.db = db
        self.pdf_processor = pdf_processor
        self.mapping_collection = db.field_mappings

    async def create_mapping(self, template_id: str, field_id: str, extracted_field_id: str, 
                            confidence: float, user_id: str) -> Dict[str, Any]:
        """Create a new mapping between a form field and an extracted field."""
        try:
            # Check if template and field exist
            template = await self.db.form_templates.find_one({"_id": ObjectId(template_id)})
            if not template:
                raise ValueError(f"Template with ID {template_id} not found")
            
            field_exists = any(field["id"] == field_id for field in template["fields"])
            if not field_exists:
                raise ValueError(f"Field with ID {field_id} not found in template {template_id}")
            
            # Create mapping
            mapping = {
                "_id": ObjectId(),
                "template_id": ObjectId(template_id),
                "field_id": field_id,
                "extracted_field_id": extracted_field_id,
                "confidence": confidence,
                "created_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True
            }
            
            await self.mapping_collection.insert_one(mapping)
            return mapping
        except Exception as e:
            logger.error(f"Error creating field mapping: {str(e)}")
            raise

    async def get_mappings_for_template(self, template_id: str) -> List[Dict[str, Any]]:
        """Get all mappings for a template."""
        try:
            cursor = self.mapping_collection.find({"template_id": ObjectId(template_id), "is_active": True})
            mappings = []
            async for mapping in cursor:
                mappings.append(mapping)
            return mappings
        except Exception as e:
            logger.error(f"Error getting mappings for template: {str(e)}")
            raise

    async def update_mapping(self, mapping_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a mapping."""
        try:
            update_data = {k: v for k, v in updates.items() if k not in ["_id", "template_id", "field_id"]}
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.mapping_collection.find_one_and_update(
                {"_id": ObjectId(mapping_id)},
                {"$set": update_data},
                return_document=True
            )
            return result
        except Exception as e:
            logger.error(f"Error updating mapping: {str(e)}")
            raise

    async def delete_mapping(self, mapping_id: str) -> bool:
        """Delete a mapping."""
        try:
            result = await self.mapping_collection.delete_one({"_id": ObjectId(mapping_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting mapping: {str(e)}")
            raise

    async def auto_map_fields(self, template_id: str, extracted_fields: List[Dict[str, Any]], 
                             user_id: str, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Automatically map extracted fields to form fields based on similarity."""
        try:
            # Get template
            template = await self.db.form_templates.find_one({"_id": ObjectId(template_id)})
            if not template:
                raise ValueError(f"Template with ID {template_id} not found")
            
            form_fields = template["fields"]
            mappings = []
            
            # For each extracted field, find the best matching form field
            for extracted_field in extracted_fields:
                best_match = None
                best_score = 0
                
                for form_field in form_fields:
                    # Skip fields that already have mappings
                    existing_mapping = await self.mapping_collection.find_one({
                        "template_id": ObjectId(template_id),
                        "field_id": form_field["id"],
                        "is_active": True
                    })
                    
                    if existing_mapping:
                        continue
                    
                    # Calculate similarity score
                    score = await self._calculate_similarity_score(extracted_field, form_field)
                    
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = form_field
                
                # Create mapping if a good match was found
                if best_match:
                    mapping = await self.create_mapping(
                        template_id=template_id,
                        field_id=best_match["id"],
                        extracted_field_id=extracted_field["id"],
                        confidence=best_score,
                        user_id=user_id
                    )
                    mappings.append(mapping)
            
            return mappings
        except Exception as e:
            logger.error(f"Error auto-mapping fields: {str(e)}")
            raise

    async def _calculate_similarity_score(self, extracted_field: Dict[str, Any], 
                                         form_field: Dict[str, Any]) -> float:
        """Calculate similarity score between an extracted field and a form field."""
        try:
            # Get field labels and names
            extracted_label = extracted_field.get("label", "").lower()
            extracted_name = extracted_field.get("name", "").lower()
            form_label = form_field.get("label", "").lower()
            form_name = form_field.get("name", "").lower()
            
            # Calculate label similarity
            label_similarity = self._calculate_text_similarity(extracted_label, form_label)
            
            # Calculate name similarity
            name_similarity = self._calculate_text_similarity(extracted_name, form_name)
            
            # Calculate type compatibility
            type_compatibility = self._calculate_type_compatibility(
                extracted_field.get("field_type", "text"),
                form_field.get("field_type", "text")
            )
            
            # Weighted average of similarities
            # Label similarity is most important, then name, then type
            weighted_score = (label_similarity * 0.5) + (name_similarity * 0.3) + (type_compatibility * 0.2)
            
            return weighted_score
        except Exception as e:
            logger.error(f"Error calculating similarity score: {str(e)}")
            return 0.0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        try:
            # Simple implementation using Levenshtein distance
            # In a production environment, you might want to use a more sophisticated algorithm
            if not text1 or not text2:
                return 0.0
            
            # Convert to sets of words for better matching
            words1 = set(text1.split())
            words2 = set(text2.split())
            
            if not words1 or not words2:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating text similarity: {str(e)}")
            return 0.0

    def _calculate_type_compatibility(self, type1: str, type2: str) -> float:
        """Calculate compatibility between two field types."""
        try:
            # Define type compatibility matrix
            compatibility_matrix = {
                "text": {"text": 1.0, "textarea": 0.8, "email": 0.7, "phone": 0.6, "number": 0.3, "date": 0.3, "checkbox": 0.1, "radio": 0.1, "select": 0.1, "file": 0.1, "hidden": 0.5},
                "textarea": {"text": 0.8, "textarea": 1.0, "email": 0.6, "phone": 0.5, "number": 0.2, "date": 0.2, "checkbox": 0.1, "radio": 0.1, "select": 0.1, "file": 0.1, "hidden": 0.5},
                "email": {"text": 0.7, "textarea": 0.6, "email": 1.0, "phone": 0.5, "number": 0.2, "date": 0.2, "checkbox": 0.1, "radio": 0.1, "select": 0.1, "file": 0.1, "hidden": 0.5},
                "phone": {"text": 0.6, "textarea": 0.5, "email": 0.5, "phone": 1.0, "number": 0.4, "date": 0.3, "checkbox": 0.1, "radio": 0.1, "select": 0.1, "file": 0.1, "hidden": 0.5},
                "number": {"text": 0.3, "textarea": 0.2, "email": 0.2, "phone": 0.4, "number": 1.0, "date": 0.5, "checkbox": 0.1, "radio": 0.1, "select": 0.1, "file": 0.1, "hidden": 0.5},
                "date": {"text": 0.3, "textarea": 0.2, "email": 0.2, "phone": 0.3, "number": 0.5, "date": 1.0, "checkbox": 0.1, "radio": 0.1, "select": 0.1, "file": 0.1, "hidden": 0.5},
                "checkbox": {"text": 0.1, "textarea": 0.1, "email": 0.1, "phone": 0.1, "number": 0.1, "date": 0.1, "checkbox": 1.0, "radio": 0.8, "select": 0.6, "file": 0.1, "hidden": 0.5},
                "radio": {"text": 0.1, "textarea": 0.1, "email": 0.1, "phone": 0.1, "number": 0.1, "date": 0.1, "checkbox": 0.8, "radio": 1.0, "select": 0.8, "file": 0.1, "hidden": 0.5},
                "select": {"text": 0.1, "textarea": 0.1, "email": 0.1, "phone": 0.1, "number": 0.1, "date": 0.1, "checkbox": 0.6, "radio": 0.8, "select": 1.0, "file": 0.1, "hidden": 0.5},
                "file": {"text": 0.1, "textarea": 0.1, "email": 0.1, "phone": 0.1, "number": 0.1, "date": 0.1, "checkbox": 0.1, "radio": 0.1, "select": 0.1, "file": 1.0, "hidden": 0.5},
                "hidden": {"text": 0.5, "textarea": 0.5, "email": 0.5, "phone": 0.5, "number": 0.5, "date": 0.5, "checkbox": 0.5, "radio": 0.5, "select": 0.5, "file": 0.5, "hidden": 1.0}
            }
            
            # Get compatibility score
            return compatibility_matrix.get(type1, {}).get(type2, 0.5)
        except Exception as e:
            logger.error(f"Error calculating type compatibility: {str(e)}")
            return 0.5

    async def generate_form_data(self, template_id: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate form data by applying mappings to extracted data."""
        try:
            # Get template
            template = await self.db.form_templates.find_one({"_id": ObjectId(template_id)})
            if not template:
                raise ValueError(f"Template with ID {template_id} not found")
            
            # Get mappings
            mappings = await this.get_mappings_for_template(template_id)
            
            # Initialize form data with default values
            form_data = {}
            for field in template["fields"]:
                form_data[field["name"]] = field.get("default_value", "")
            
            # Apply mappings
            for mapping in mappings:
                field_id = mapping["field_id"]
                extracted_field_id = mapping["extracted_field_id"]
                
                # Find the field in the template
                field = next((f for f in template["fields"] if f["id"] == field_id), None)
                if not field:
                    continue
                
                # Find the extracted field
                extracted_value = extracted_data.get(extracted_field_id)
                if extracted_value is not None:
                    form_data[field["name"]] = extracted_value
            
            return form_data
        except Exception as e:
            logger.error(f"Error generating form data: {str(e)}")
            raise 