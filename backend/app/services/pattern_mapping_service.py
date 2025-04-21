import re
import logging
from typing import List, Dict, Any, Optional, Callable
from uuid import UUID
import ast
import json

from app.models.field_mapping import PatternRule, FieldTransformation, ValidationRule
from app.core.supabase import get_supabase
from app.core.errors import ValidationError

logger = logging.getLogger(__name__)

class PatternMappingService:
    def __init__(self, workspace_id: UUID):
        self.workspace_id = workspace_id
        self.supabase = get_supabase()
        self._pattern_rules_cache = None
        self._transformations_cache = None
        self._validation_rules_cache = None

    async def get_pattern_rules(self, refresh_cache: bool = False) -> List[PatternRule]:
        """Get all active pattern-based rules for the workspace."""
        if self._pattern_rules_cache is None or refresh_cache:
            response = await self.supabase.table("pattern_rules").select("*").eq(
                "workspace_id", str(self.workspace_id)
            ).eq("is_active", True).order("priority", desc=True).execute()
            
            self._pattern_rules_cache = [PatternRule(**rule) for rule in response.data]
        
        return self._pattern_rules_cache

    async def get_transformations(self, refresh_cache: bool = False) -> List[FieldTransformation]:
        """Get all active field transformations for the workspace."""
        if self._transformations_cache is None or refresh_cache:
            response = await self.supabase.table("field_transformations").select("*").eq(
                "workspace_id", str(self.workspace_id)
            ).eq("is_active", True).execute()
            
            self._transformations_cache = [FieldTransformation(**trans) for trans in response.data]
        
        return self._transformations_cache

    async def get_validation_rules(self, refresh_cache: bool = False) -> List[ValidationRule]:
        """Get all active validation rules for the workspace."""
        if self._validation_rules_cache is None or refresh_cache:
            response = await self.supabase.table("validation_rules").select("*").eq(
                "workspace_id", str(self.workspace_id)
            ).eq("is_active", True).execute()
            
            self._validation_rules_cache = [ValidationRule(**rule) for rule in response.data]
        
        return self._validation_rules_cache

    async def create_pattern_rule(self, rule: PatternRule) -> PatternRule:
        """Create a new pattern-based rule."""
        response = await self.supabase.table("pattern_rules").insert(
            rule.dict(exclude={'id'})
        ).execute()
        
        self._pattern_rules_cache = None  # Invalidate cache
        return PatternRule(**response.data[0])

    async def create_transformation(self, transformation: FieldTransformation) -> FieldTransformation:
        """Create a new field transformation."""
        response = await self.supabase.table("field_transformations").insert(
            transformation.dict(exclude={'id'})
        ).execute()
        
        self._transformations_cache = None  # Invalidate cache
        return FieldTransformation(**response.data[0])

    async def create_validation_rule(self, rule: ValidationRule) -> ValidationRule:
        """Create a new validation rule."""
        response = await this.supabase.table("validation_rules").insert(
            rule.dict(exclude={'id'})
        ).execute()
        
        this._validation_rules_cache = None  # Invalidate cache
        return ValidationRule(**response.data[0])

    async def apply_pattern_rules(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Apply pattern-based rules to a field name."""
        rules = await this.get_pattern_rules()
        
        for rule in rules:
            if re.match(rule.pattern, field_name):
                result = {
                    "target_field": rule.target_field,
                    "confidence": rule.confidence_threshold,
                    "rule_id": rule.id
                }
                
                # Apply transformation if specified
                if rule.transformation:
                    transformation = await this._get_transformation(rule.transformation)
                    if transformation:
                        result["transformed_field"] = await this._apply_transformation(
                            field_name, transformation
                        )
                
                return result
        
        return None

    async def _get_transformation(self, transformation_name: str) -> Optional[FieldTransformation]:
        """Get a transformation by name."""
        transformations = await this.get_transformations()
        for trans in transformations:
            if trans.name == transformation_name:
                return trans
        return None

    async def _apply_transformation(self, field_name: str, transformation: FieldTransformation) -> str:
        """Apply a transformation to a field name."""
        if transformation.transformation_type == "camelCase":
            return self._to_camel_case(field_name)
        elif transformation.transformation_type == "snake_case":
            return self._to_snake_case(field_name)
        elif transformation.transformation_type == "kebab-case":
            return self._to_kebab_case(field_name)
        elif transformation.transformation_type == "PascalCase":
            return self._to_pascal_case(field_name)
        elif transformation.transformation_type == "custom":
            return await this._apply_custom_transformation(field_name, transformation.transformation_logic)
        else:
            return field_name

    def _to_camel_case(self, field_name: str) -> str:
        """Convert a field name to camelCase."""
        words = re.split(r'[-_\s]', field_name.lower())
        return words[0] + ''.join(word.capitalize() for word in words[1:])

    def _to_snake_case(self, field_name: str) -> str:
        """Convert a field name to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', field_name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _to_kebab_case(self, field_name: str) -> str:
        """Convert a field name to kebab-case."""
        return self._to_snake_case(field_name).replace('_', '-')

    def _to_pascal_case(self, field_name: str) -> str:
        """Convert a field name to PascalCase."""
        words = re.split(r'[-_\s]', field_name.lower())
        return ''.join(word.capitalize() for word in words)

    async def _apply_custom_transformation(self, field_name: str, transformation_logic: str) -> str:
        """Apply a custom transformation to a field name."""
        try:
            # Create a safe environment for executing the transformation
            safe_env = {
                'field_name': field_name,
                're': re,
                'json': json
            }
            
            # Execute the transformation logic
            exec(f"result = {transformation_logic}", safe_env)
            return safe_env.get('result', field_name)
        except Exception as e:
            logger.error(f"Error applying custom transformation: {str(e)}")
            return field_name

    async def validate_field(self, field_name: str, field_value: Any) -> List[str]:
        """Validate a field value against validation rules."""
        errors = []
        rules = await this.get_validation_rules()
        
        for rule in rules:
            if rule.field_name == field_name:
                is_valid, error_message = await this._apply_validation(rule, field_value)
                if not is_valid:
                    errors.append(error_message)
        
        return errors

    async def _apply_validation(self, rule: ValidationRule, value: Any) -> tuple[bool, str]:
        """Apply a validation rule to a value."""
        try:
            if rule.validation_type == "regex":
                pattern = re.compile(rule.validation_logic)
                is_valid = bool(pattern.match(str(value)))
            elif rule.validation_type == "range":
                range_values = json.loads(rule.validation_logic)
                min_val, max_val = range_values.get("min"), range_values.get("max")
                is_valid = (min_val is None or value >= min_val) and (max_val is None or value <= max_val)
            elif rule.validation_type == "enum":
                allowed_values = json.loads(rule.validation_logic)
                is_valid = value in allowed_values
            elif rule.validation_type == "custom":
                # Create a safe environment for executing the validation
                safe_env = {
                    'value': value,
                    're': re,
                    'json': json
                }
                
                # Execute the validation logic
                exec(f"is_valid = {rule.validation_logic}", safe_env)
                is_valid = safe_env.get('is_valid', False)
            else:
                is_valid = True
            
            return is_valid, rule.error_message if not is_valid else ""
        except Exception as e:
            logger.error(f"Error applying validation: {str(e)}")
            return False, f"Validation error: {str(e)}" 