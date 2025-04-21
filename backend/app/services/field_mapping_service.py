import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime
import spacy
from difflib import SequenceMatcher
import re
from fastapi import HTTPException

from app.models.field_mapping import (
    FieldMappingRule,
    FieldMappingCorrection,
    FieldMappingSuggestions,
    MappingSuggestion,
    FieldMappingResult
)
from app.core.supabase import get_supabase
from app.services.pattern_mapping_service import PatternMappingService

logger = logging.getLogger(__name__)

# Load spaCy model for semantic similarity
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    logger.warning("Downloading spaCy model...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load('en_core_web_sm')

class FieldMappingService:
    def __init__(self, workspace_id: UUID):
        self.workspace_id = workspace_id
        self.supabase = get_supabase()
        self._rules_cache = None
        self._corrections_cache = None

    async def get_rules(self, refresh_cache: bool = False) -> List[FieldMappingRule]:
        """Get all active field mapping rules for the workspace."""
        if self._rules_cache is None or refresh_cache:
            response = await self.supabase.table("field_mapping_rules").select("*").eq(
                "workspace_id", str(self.workspace_id)
            ).eq("is_active", True).order("priority", desc=True).execute()
            
            self._rules_cache = [FieldMappingRule(**rule) for rule in response.data]
        
        return self._rules_cache

    async def get_corrections(self, refresh_cache: bool = False) -> List[FieldMappingCorrection]:
        """Get all field mapping corrections for the workspace."""
        if self._corrections_cache is None or refresh_cache:
            response = await self.supabase.table("field_mapping_corrections").select("*").eq(
                "workspace_id", str(self.workspace_id)
            ).execute()
            
            self._corrections_cache = [FieldMappingCorrection(**corr) for corr in response.data]
        
        return self._corrections_cache

    async def create_rule(self, rule: FieldMappingRule) -> FieldMappingRule:
        """Create a new field mapping rule."""
        response = await self.supabase.table("field_mapping_rules").insert(
            rule.dict(exclude={'id'})
        ).execute()
        
        self._rules_cache = None  # Invalidate cache
        return FieldMappingRule(**response.data[0])

    async def create_correction(self, correction: FieldMappingCorrection) -> FieldMappingCorrection:
        """Create a new field mapping correction."""
        response = await self.supabase.table("field_mapping_corrections").insert(
            correction.dict(exclude={'id'})
        ).execute()
        
        self._corrections_cache = None  # Invalidate cache
        return FieldMappingCorrection(**response.data[0])

    def _preprocess_field_name(self, field: str) -> str:
        """Preprocess field name for better matching."""
        # Convert camelCase and PascalCase to snake_case
        field = re.sub('([a-z0-9])([A-Z])', r'\1_\2', field)
        field = re.sub('([A-Z])([A-Z][a-z])', r'\1_\2', field)
        
        # Replace common separators with spaces
        field = re.sub('[_\-./]', ' ', field)
        
        # Convert to lowercase and strip whitespace
        field = field.lower().strip()
        
        return field

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using SequenceMatcher."""
        return SequenceMatcher(None, str1, str2).ratio()

    def _calculate_semantic_similarity(self, doc1: spacy.tokens.Doc, doc2: spacy.tokens.Doc) -> float:
        """Calculate semantic similarity between two spaCy docs."""
        if not doc1.vector_norm or not doc2.vector_norm:
            return 0.0
        return doc1.similarity(doc2)

    async def _get_common_field_mappings(self) -> Dict[str, List[str]]:
        """Get common field mappings from historical data."""
        common_mappings = {
            "dob": ["birth_date", "date_of_birth", "birthdate"],
            "ssn": ["social_security_number", "social_security", "tax_id"],
            "fname": ["first_name", "given_name", "firstname"],
            "lname": ["last_name", "surname", "lastname"],
            "addr": ["address", "street_address", "mailing_address"],
            "zip": ["postal_code", "zipcode", "zip_code"],
            "tel": ["phone", "telephone", "phone_number", "mobile"],
            "email": ["email_address", "mail", "electronic_mail"],
        }
        return common_mappings

    async def map_field(self, source_field: str, context: Dict[str, Any]) -> FieldMappingResult:
        """
        Map a field using rules, corrections, and AI suggestions.
        
        Args:
            source_field: The field name to map
            context: Additional context (e.g., surrounding text, document type)
            
        Returns:
            FieldMappingResult containing the mapping and suggestions
        """
        # 1. Check pattern-based rules first
        pattern_service = PatternMappingService(self.workspace_id)
        pattern_result = await pattern_service.apply_pattern_rules(source_field)
        if pattern_result:
            return FieldMappingResult(
                source_field=source_field,
                mapped_field=pattern_result["target_field"],
                confidence=pattern_result["confidence"],
                rule_applied=pattern_result["rule_id"],
                context=context
            )

        # 2. Check explicit rules
        rules = await self.get_rules()
        for rule in rules:
            if rule.source_field.lower() == source_field.lower():
                return FieldMappingResult(
                    source_field=source_field,
                    mapped_field=rule.target_field,
                    confidence=1.0,
                    rule_applied=rule.id,
                    context=context
                )

        # 3. Check previous corrections
        corrections = await self.get_corrections()
        similar_corrections = [
            c for c in corrections
            if c.source_field.lower() == source_field.lower()
        ]
        if similar_corrections:
            # Use the most recent correction
            latest = max(similar_corrections, key=lambda x: x.created_at)
            return FieldMappingResult(
                source_field=source_field,
                mapped_field=latest.corrected_mapping,
                confidence=0.9,  # High confidence due to human correction
                context=context
            )

        # 4. Use AI to generate suggestions
        suggestions = await this._generate_ai_suggestions(source_field, context)
        
        # 5. If we have high-confidence suggestion, use it
        if suggestions and suggestions[0].confidence >= 0.7:
            return FieldMappingResult(
                source_field=source_field,
                mapped_field=suggestions[0].field,
                confidence=suggestions[0].confidence,
                suggestions=suggestions,
                context=context
            )
        
        # 6. Return low-confidence result with suggestions
        return FieldMappingResult(
            source_field=source_field,
            mapped_field=source_field,  # Keep original as fallback
            confidence=0.0,
            suggestions=suggestions,
            context=context
        )

    async def _generate_ai_suggestions(
        self, source_field: str, context: Dict[str, Any]
    ) -> List[MappingSuggestion]:
        """
        Generate AI-powered suggestions for field mapping using multiple techniques:
        1. Common field mappings lookup
        2. Semantic similarity using spaCy
        3. String similarity for handling typos and variations
        4. Context-aware mapping using document type and surrounding text
        """
        suggestions = []
        preprocessed_source = self._preprocess_field_name(source_field)
        source_doc = nlp(preprocessed_source)
        
        # 1. Check common field mappings
        common_mappings = await self._get_common_field_mappings()
        for standard_field, variations in common_mappings.items():
            # Check if source field matches any variation
            if preprocessed_source in variations or any(
                self._calculate_string_similarity(preprocessed_source, var) > 0.8
                for var in variations
            ):
                suggestions.append(MappingSuggestion(
                    field=standard_field,
                    confidence=0.9,
                    explanation="Matched common field mapping"
                ))

        # 2. Use document type context if available
        doc_type = context.get("document_type", "").lower()
        if doc_type:
            # Get field mappings specific to document type
            type_specific_fields = {
                "medical_record": {
                    "dob": 0.9,
                    "patient_id": 0.9,
                    "diagnosis": 0.9
                },
                "tax_form": {
                    "ssn": 0.9,
                    "tax_year": 0.9,
                    "income": 0.9
                },
                "invoice": {
                    "invoice_number": 0.9,
                    "amount": 0.9,
                    "due_date": 0.9
                }
            }
            
            if doc_type in type_specific_fields:
                for field, confidence in type_specific_fields[doc_type].items():
                    field_doc = nlp(self._preprocess_field_name(field))
                    semantic_sim = self._calculate_semantic_similarity(source_doc, field_doc)
                    if semantic_sim > 0.7:
                        suggestions.append(MappingSuggestion(
                            field=field,
                            confidence=semantic_sim * confidence,
                            explanation=f"Based on document type: {doc_type}"
                        ))

        # 3. Use surrounding text context if available
        surrounding_text = context.get("surrounding_text", "")
        if surrounding_text:
            # Extract potential field names from surrounding text
            # This is a simplified example - you might want to use more sophisticated NLP here
            context_doc = nlp(surrounding_text.lower())
            for token in context_doc:
                if token.pos_ in ["NOUN", "PROPN"]:
                    token_doc = nlp(token.text)
                    semantic_sim = self._calculate_semantic_similarity(source_doc, token_doc)
                    if semantic_sim > 0.7:
                        suggestions.append(MappingSuggestion(
                            field=token.text,
                            confidence=semantic_sim * 0.8,
                            explanation="Extracted from surrounding text"
                        ))

        # 4. Get historical corrections for similar fields
        corrections = await self.get_corrections()
        for correction in corrections:
            if correction.source_field != source_field:  # Don't suggest exact matches
                source_sim = self._calculate_string_similarity(
                    preprocessed_source,
                    self._preprocess_field_name(correction.source_field)
                )
                if source_sim > 0.7:
                    suggestions.append(MappingSuggestion(
                        field=correction.corrected_mapping,
                        confidence=source_sim * 0.85,
                        explanation="Based on similar historical correction"
                    ))

        # Remove duplicates and sort by confidence
        unique_suggestions = {}
        for suggestion in suggestions:
            if suggestion.field not in unique_suggestions or \
               suggestion.confidence > unique_suggestions[suggestion.field].confidence:
                unique_suggestions[suggestion.field] = suggestion

        sorted_suggestions = sorted(
            unique_suggestions.values(),
            key=lambda x: x.confidence,
            reverse=True
        )

        return sorted_suggestions[:5]  # Return top 5 suggestions

    async def apply_correction(
        self, 
        source_field: str, 
        original_mapping: str, 
        corrected_mapping: str,
        context: Optional[Dict[str, Any]] = None,
        document_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> Tuple[FieldMappingCorrection, Optional[FieldMappingRule]]:
        """
        Apply a correction and optionally create a rule if the correction is frequent.
        
        Returns:
            Tuple of (created correction, created rule if any)
        """
        # Create the correction
        correction = FieldMappingCorrection(
            workspace_id=self.workspace_id,
            source_field=source_field,
            original_mapping=original_mapping,
            corrected_mapping=corrected_mapping,
            context=context,
            document_id=document_id,
            created_by=user_id
        )
        created_correction = await self.create_correction(correction)
        
        # Check if this correction is frequent enough to create a rule
        corrections = await self.get_corrections(refresh_cache=True)
        similar_corrections = [
            c for c in corrections
            if c.source_field.lower() == source_field.lower()
            and c.corrected_mapping.lower() == corrected_mapping.lower()
        ]
        
        # If we have 3 or more similar corrections, create a rule
        if len(similar_corrections) >= 3:
            rule = FieldMappingRule(
                workspace_id=self.workspace_id,
                source_field=source_field,
                target_field=corrected_mapping,
                confidence_threshold=0.8,
                created_by=user_id,
                metadata={
                    "created_from_corrections": [str(c.id) for c in similar_corrections],
                    "correction_count": len(similar_corrections)
                }
            )
            created_rule = await self.create_rule(rule)
            return created_correction, created_rule
        
        return created_correction, None

    async def update_rule(self, rule_id: UUID, rule: FieldMappingRule) -> FieldMappingRule:
        """Update an existing field mapping rule."""
        response = await self.supabase.table("field_mapping_rules").update(
            rule.dict(exclude={'id'})
        ).eq("id", str(rule_id)).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        self._rules_cache = None  # Invalidate cache
        return FieldMappingRule(**response.data[0])

    async def delete_rule(self, rule_id: UUID) -> None:
        """Delete a field mapping rule."""
        response = await self.supabase.table("field_mapping_rules").delete().eq(
            "id", str(rule_id)
        ).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        self._rules_cache = None  # Invalidate cache

    async def record_suggestion_feedback(
        self,
        source_field: str,
        suggested_field: str,
        was_helpful: bool,
        feedback_text: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> None:
        """Record feedback on a field mapping suggestion."""
        feedback = {
            "workspace_id": str(self.workspace_id),
            "source_field": source_field,
            "suggested_field": suggested_field,
            "was_helpful": was_helpful,
            "feedback_text": feedback_text,
            "created_by": str(user_id) if user_id else None
        }
        
        await self.supabase.table("field_mapping_feedback").insert(feedback).execute()

    async def get_mapping_analytics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get analytics about field mapping performance."""
        # Build date filter
        date_filter = ""
        if start_date and end_date:
            date_filter = f"created_at.gte.{start_date},created_at.lte.{end_date}"
        elif start_date:
            date_filter = f"created_at.gte.{start_date}"
        elif end_date:
            date_filter = f"created_at.lte.{end_date}"

        # Get mapping success rate
        corrections = await self.supabase.table("field_mapping_corrections").select(
            "*"
        ).eq("workspace_id", str(self.workspace_id)).execute()
        
        total_mappings = len(corrections.data)
        successful_mappings = len([
            c for c in corrections.data
            if c["confidence"] >= 0.8
        ])
        
        # Get suggestion feedback
        feedback = await self.supabase.table("field_mapping_feedback").select(
            "*"
        ).eq("workspace_id", str(self.workspace_id)).execute()
        
        total_feedback = len(feedback.data)
        helpful_suggestions = len([
            f for f in feedback.data
            if f["was_helpful"]
        ])
        
        # Get rule usage statistics
        rules = await self.get_rules()
        rule_usage = {}
        for rule in rules:
            rule_corrections = len([
                c for c in corrections.data
                if c["rule_id"] == str(rule.id)
            ])
            rule_usage[rule.source_field] = rule_corrections

        return {
            "total_mappings": total_mappings,
            "successful_mappings": successful_mappings,
            "mapping_success_rate": successful_mappings / total_mappings if total_mappings > 0 else 0,
            "total_feedback": total_feedback,
            "helpful_suggestions": helpful_suggestions,
            "suggestion_helpfulness_rate": helpful_suggestions / total_feedback if total_feedback > 0 else 0,
            "rule_usage": rule_usage,
            "most_used_rules": sorted(
                rule_usage.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    async def bulk_create_rules(self, rules: List[FieldMappingRule]) -> List[FieldMappingRule]:
        """Create multiple field mapping rules at once."""
        created_rules = []
        for rule in rules:
            rule.workspace_id = self.workspace_id
            created_rule = await self.create_rule(rule)
            created_rules.append(created_rule)
        return created_rules

    async def bulk_update_rules(self, operations: List[BulkRuleOperation]) -> List[FieldMappingRule]:
        """Update multiple field mapping rules at once."""
        updated_rules = []
        for operation in operations:
            rule = await self.get_rule(operation.rule_id)
            if not rule:
                raise HTTPException(status_code=404, detail=f"Rule {operation.rule_id} not found")
            
            # Update rule fields based on operation
            for field, value in operation.updates.items():
                setattr(rule, field, value)
            
            updated_rule = await self.update_rule(operation.rule_id, rule)
            updated_rules.append(updated_rule)
        return updated_rules

    async def bulk_delete_rules(self, rule_ids: List[UUID]) -> None:
        """Delete multiple field mapping rules at once."""
        for rule_id in rule_ids:
            await self.delete_rule(rule_id)

    async def batch_map_fields(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map fields for multiple documents at once."""
        results = []
        for document in documents:
            source_fields = document.get("fields", {})
            context = document.get("context", {})
            
            mapped_fields = {}
            for source_field, value in source_fields.items():
                result = await self.map_field(source_field, context)
                mapped_fields[result.mapped_field] = value
            
            results.append({
                "document_id": document.get("id"),
                "mapped_fields": mapped_fields,
                "confidence": min(result.confidence for result in results) if results else 0.0
            })
        
        return results 