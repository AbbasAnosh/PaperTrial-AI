"""
Service for handling natural language processing tasks, including question answering
and field value extraction from user responses.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from transformers import pipeline
import spacy
import re
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class NLPService:
    """Service for handling natural language processing tasks."""

    def __init__(self):
        """Initialize the NLP service."""
        try:
            # Load spaCy model for entity recognition and text processing
            self.nlp = spacy.load("en_core_web_sm")
            
            # Initialize question answering pipeline
            self.qa_pipeline = pipeline(
                "question-answering",
                model="deepset/roberta-base-squad2",
                device=0 if settings.USE_GPU else -1
            )
            
            # Initialize text classification pipeline
            self.classifier = pipeline(
                "text-classification",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=0 if settings.USE_GPU else -1
            )
            
            # Initialize token classification pipeline for entity extraction
            self.ner_pipeline = pipeline(
                "token-classification",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                device=0 if settings.USE_GPU else -1
            )
        except Exception as e:
            logger.error(f"Failed to initialize NLP service: {str(e)}")
            raise

    async def process_question(self, question: str, context: str) -> Dict[str, Any]:
        """Process a natural language question and extract relevant information."""
        try:
            # Get answer from QA pipeline
            qa_result = self.qa_pipeline(
                question=question,
                context=context,
                max_answer_len=50,
                handle_impossible_answer=True
            )
            
            # Extract entities from the answer
            doc = self.nlp(qa_result["answer"])
            entities = [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                }
                for ent in doc.ents
            ]
            
            # Get sentiment of the answer
            sentiment = self.classifier(qa_result["answer"])[0]
            
            return {
                "answer": qa_result["answer"],
                "confidence": qa_result["score"],
                "entities": entities,
                "sentiment": sentiment,
                "context_used": qa_result["context"]
            }
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            raise

    async def extract_field_value(self, text: str, field_type: str) -> Tuple[Any, float]:
        """Extract a field value from text based on the field type."""
        try:
            confidence = 1.0
            value = None
            
            if field_type == "text":
                value = text.strip()
            
            elif field_type == "number":
                # Extract numbers from text
                numbers = re.findall(r"[-+]?\d*\.\d+|\d+", text)
                if numbers:
                    value = float(numbers[0])
                    confidence = 0.9
                else:
                    confidence = 0.0
            
            elif field_type == "email":
                # Extract email addresses
                emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
                if emails:
                    value = emails[0]
                    confidence = 0.95
                else:
                    confidence = 0.0
            
            elif field_type == "phone":
                # Extract phone numbers
                phones = re.findall(r"\+?[\d\s-()]{10,}", text)
                if phones:
                    value = phones[0].strip()
                    confidence = 0.9
                else:
                    confidence = 0.0
            
            elif field_type == "date":
                # Extract dates
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ in ["DATE", "TIME"]:
                        value = ent.text
                        confidence = 0.85
                        break
                if not value:
                    confidence = 0.0
            
            elif field_type == "checkbox":
                # Determine if the text indicates a positive response
                positive_words = ["yes", "true", "1", "checked", "selected", "agree"]
                value = any(word in text.lower() for word in positive_words)
                confidence = 0.8
            
            elif field_type in ["radio", "select"]:
                # Extract options from text
                doc = this.nlp(text)
                options = [token.text for token in doc if token.pos_ in ["NOUN", "PROPN"]]
                if options:
                    value = options[0]
                    confidence = 0.7
                else:
                    confidence = 0.0
            
            return value, confidence
        except Exception as e:
            logger.error(f"Error extracting field value: {str(e)}")
            return None, 0.0

    async def generate_questions(self, field: Dict[str, Any], context: str) -> List[str]:
        """Generate natural language questions for a form field."""
        try:
            questions = []
            
            # Basic question template
            base_question = f"What is the {field['label'].lower()}?"
            
            # Add field-specific context
            if field.get("help_text"):
                base_question += f" ({field['help_text']})"
            
            questions.append(base_question)
            
            # Add alternative phrasings
            if field["field_type"] == "text":
                questions.extend([
                    f"Please provide the {field['label'].lower()}",
                    f"Enter the {field['label'].lower()}",
                    f"Type in the {field['label'].lower()}"
                ])
            elif field["field_type"] == "number":
                questions.extend([
                    f"What is the numeric value for {field['label'].lower()}?",
                    f"Enter the number for {field['label'].lower()}",
                    f"Provide the numerical value for {field['label'].lower()}"
                ])
            elif field["field_type"] == "email":
                questions.extend([
                    f"What is your email address for {field['label'].lower()}?",
                    f"Enter your email for {field['label'].lower()}",
                    f"Provide your email address for {field['label'].lower()}"
                ])
            elif field["field_type"] == "phone":
                questions.extend([
                    f"What is your phone number for {field['label'].lower()}?",
                    f"Enter your contact number for {field['label'].lower()}",
                    f"Provide your phone number for {field['label'].lower()}"
                ])
            elif field["field_type"] == "date":
                questions.extend([
                    f"What is the date for {field['label'].lower()}?",
                    f"Enter the date for {field['label'].lower()}",
                    f"Provide the date for {field['label'].lower()}"
                ])
            elif field["field_type"] == "checkbox":
                questions.extend([
                    f"Do you want to {field['label'].lower()}?",
                    f"Would you like to {field['label'].lower()}?",
                    f"Should we {field['label'].lower()}?"
                ])
            
            return questions
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            return [f"What is the {field['label'].lower()}?"]

    async def validate_response(self, response: str, field: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a user's response against field requirements."""
        try:
            # Check if response is empty
            if not response.strip():
                if field.get("required", False):
                    return False, f"{field['label']} is required"
                return True, ""

            # Extract value and confidence
            value, confidence = await this.extract_field_value(response, field["field_type"])
            
            # Check confidence threshold
            if confidence < field.get("confidence_threshold", 0.7):
                return False, f"Could not confidently extract {field['label']} from the response"

            # Apply validation rules
            if field.get("validation_rules"):
                for rule in field["validation_rules"]:
                    if not await this._apply_validation_rule(rule, value):
                        return False, rule["message"]

            return True, ""
        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            return False, str(e)

    async def _apply_validation_rule(self, rule: Dict[str, Any], value: Any) -> bool:
        """Apply a validation rule to a value."""
        try:
            rule_type = rule["rule_type"]
            
            if rule_type == "min_length":
                return len(str(value)) >= rule["value"]
            
            elif rule_type == "max_length":
                return len(str(value)) <= rule["value"]
            
            elif rule_type == "min_value":
                return float(value) >= float(rule["value"])
            
            elif rule_type == "max_value":
                return float(value) <= float(rule["value"])
            
            elif rule_type == "pattern":
                return bool(re.match(rule["value"], str(value)))
            
            elif rule_type == "custom":
                # Custom validation logic could be implemented here
                return True
            
            return True
        except Exception as e:
            logger.error(f"Error applying validation rule: {str(e)}")
            return False 