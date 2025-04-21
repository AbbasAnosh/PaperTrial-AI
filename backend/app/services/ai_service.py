from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from pydantic import BaseModel, Field, validator
import json
import logging
import asyncio
import functools
import time
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FormField(BaseModel):
    """Model for form field analysis"""
    field_name: str = Field(description="The name of the form field")
    field_type: str = Field(description="The type of the form field (text, select, file, etc.)")
    value: str = Field(description="The resolved value for the field")
    confidence: float = Field(description="Confidence score for the value resolution")
    explanation: str = Field(description="Explanation of how the value was determined")
    selector_hint: Optional[str] = Field(description="CSS selector hint for finding the field", default=None)
    label_text: Optional[str] = Field(description="Label text associated with the field", default=None)
    placeholder: Optional[str] = Field(description="Placeholder text for the field", default=None)
    aria_label: Optional[str] = Field(description="ARIA label for the field", default=None)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v

class FormAnalysis(BaseModel):
    """Model for form analysis results"""
    fields: List[FormField] = Field(description="List of analyzed form fields")
    confidence: float = Field(description="Overall confidence in the analysis")
    suggestions: List[str] = Field(description="Suggestions for improving the form")
    form_type: Optional[str] = Field(description="Classified form type (e.g., visa, tax, benefits)", default=None)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v

class ValidationResult(BaseModel):
    """Model for form validation results"""
    valid: bool = Field(description="Whether the form data is valid")
    errors: List[str] = Field(description="List of validation errors")
    warnings: List[str] = Field(description="List of validation warnings")
    field_validations: Dict[str, Dict[str, Any]] = Field(
        description="Detailed validation results for each field",
        default_factory=dict
    )

class FormFillStatus(BaseModel):
    """Model for tracking form fill status"""
    field: str = Field(description="Field name or action")
    status: str = Field(description="Status of the operation (filled, clicked, error, etc.)")
    value: Optional[str] = Field(description="Value that was filled or action taken", default=None)
    timestamp: str = Field(description="ISO timestamp of the operation")
    error: Optional[str] = Field(description="Error message if status is error", default=None)
    selector_used: Optional[str] = Field(description="Selector used to find the field", default=None)

class AIServiceConfig:
    """Configuration for AIService"""
    def __init__(
        self,
        model_name: str = "gpt-4-turbo-preview",
        temperature: float = 0.1,
        max_tokens: int = 1000,
        cache_ttl: int = 3600,  # 1 hour
        max_retries: int = 3,
        timeout: int = 30,
        streaming: bool = False,
        simulation_mode: bool = False,
        debug_mode: bool = False
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.timeout = timeout
        self.streaming = streaming
        self.simulation_mode = simulation_mode
        self.debug_mode = debug_mode

class AIService:
    def __init__(self, config: Optional[AIServiceConfig] = None):
        self.config = config or AIServiceConfig()
        
        # Set up callback manager for streaming if enabled
        callback_manager = None
        if self.config.streaming:
            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        
        # Initialize LLM with configuration
        self.llm = ChatOpenAI(
            model_name=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            callback_manager=callback_manager
        )
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize parsers
        self.form_analysis_parser = PydanticOutputParser(pydantic_object=FormAnalysis)
        self.validation_result_parser = PydanticOutputParser(pydantic_object=ValidationResult)
        
        # Initialize cache
        self._cache = {}
        self._cache_timestamps = {}
        
        # Initialize status tracking
        self._fill_status_history: List[FormFillStatus] = []
    
    def _get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate a cache key from function name and arguments"""
        key_parts = [func_name]
        key_parts.extend([str(arg) for arg in args])
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        return ":".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache if it exists and is not expired"""
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.config.cache_ttl:
                logger.debug(f"Cache hit for {cache_key}")
                return self._cache[cache_key]
            else:
                logger.debug(f"Cache expired for {cache_key}")
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
        return None
    
    def _set_in_cache(self, cache_key: str, value: Any) -> None:
        """Set value in cache with current timestamp"""
        self._cache[cache_key] = value
        self._cache_timestamps[cache_key] = time.time()
        logger.debug(f"Cached result for {cache_key}")
    
    def _add_status_entry(self, field: str, status: str, value: Optional[str] = None, 
                          error: Optional[str] = None, selector_used: Optional[str] = None) -> None:
        """Add a status entry to the history"""
        status_entry = FormFillStatus(
            field=field,
            status=status,
            value=value,
            timestamp=datetime.now().isoformat(),
            error=error,
            selector_used=selector_used
        )
        self._fill_status_history.append(status_entry)
        logger.info(f"Form fill status: {field} - {status}")
    
    def get_fill_status_history(self) -> List[FormFillStatus]:
        """Get the complete history of form fill operations"""
        return self._fill_status_history
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception)),
        reraise=True
    )
    async def _execute_chain(self, chain: LLMChain, **kwargs) -> Any:
        """Execute a chain with retry logic and timeout"""
        try:
            return await asyncio.wait_for(
                chain.arun(**kwargs),
                timeout=self.config.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {self.config.timeout} seconds")
            raise
    
    async def resolve_template(self, template: str, user_data: Dict[str, Any], documents: Dict[str, str]) -> str:
        """Resolve a template string using user data and documents"""
        cache_key = self._get_cache_key("resolve_template", template, user_data, documents)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a template resolution assistant. Your task is to resolve template strings using provided user data and documents.
            Template format: {{user.field_name}} or {{documents.document_name}}
            Always return just the resolved value, nothing else."""),
            ("user", "Template: {template}\nUser Data: {user_data}\nDocuments: {documents}")
        ])

        chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            memory=self.memory
        )

        try:
            result = await self._execute_chain(
                chain,
                template=template,
                user_data=json.dumps(user_data),
                documents=json.dumps(documents)
            )
            result = result.strip()
            self._set_in_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error resolving template: {str(e)}", exc_info=True)
            return template

    async def analyze_form_fields(self, form_data: Dict[str, Any]) -> FormAnalysis:
        """Analyze form fields and suggest improvements"""
        cache_key = self._get_cache_key("analyze_form_fields", form_data)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a form analysis assistant. Analyze the provided form data and:
            1. Identify each field's type and purpose
            2. Resolve field values with confidence scores
            3. Suggest improvements for the form
            4. Provide explanations for your decisions
            5. Classify the form type (e.g., visa, tax, benefits)
            6. Provide selector hints for finding fields
            7. Extract label text, placeholder, and aria-label information
            
            Format your response according to the FormAnalysis schema."""),
            ("user", "Form Data: {form_data}")
        ])

        chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            memory=self.memory
        )

        try:
            result = await self._execute_chain(
                chain,
                form_data=json.dumps(form_data)
            )
            parsed_result = self.form_analysis_parser.parse(result)
            self._set_in_cache(cache_key, parsed_result)
            return parsed_result
        except Exception as e:
            logger.error(f"Error analyzing form fields: {str(e)}", exc_info=True)
            return FormAnalysis(
                fields=[],
                confidence=0.0,
                suggestions=["Error during analysis"],
                form_type=None
            )

    async def validate_form_data(self, form_data: Dict[str, Any], form_config: Dict[str, Any]) -> ValidationResult:
        """Validate form data against configuration"""
        cache_key = self._get_cache_key("validate_form_data", form_data, form_config)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a form validation assistant. Validate the provided form data against the form configuration.
            Check for:
            1. Required fields
            2. Field types and formats
            3. Value constraints
            4. Document requirements
            
            Return a validation result with errors and warnings in the ValidationResult format."""),
            ("user", "Form Data: {form_data}\nForm Config: {form_config}")
        ])

        chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            memory=self.memory
        )

        try:
            result = await self._execute_chain(
                chain,
                form_data=json.dumps(form_data),
                form_config=json.dumps(form_config)
            )
            parsed_result = self.validation_result_parser.parse(result)
            self._set_in_cache(cache_key, parsed_result)
            return parsed_result
        except Exception as e:
            logger.error(f"Error validating form data: {str(e)}", exc_info=True)
            return ValidationResult(
                valid=False,
                errors=["Error during validation"],
                warnings=[],
                field_validations={}
            )

    async def generate_form_instructions(self, form_config: Dict[str, Any]) -> str:
        """Generate human-readable instructions for a form"""
        cache_key = self._get_cache_key("generate_form_instructions", form_config)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a form instruction generator. Create clear, concise instructions for filling out the form.
            Include:
            1. Required information and documents
            2. Step-by-step guidance
            3. Common mistakes to avoid
            4. Tips for successful submission"""),
            ("user", "Form Config: {form_config}")
        ])

        chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            memory=self.memory
        )

        try:
            result = await self._execute_chain(
                chain,
                form_config=json.dumps(form_config)
            )
            self._set_in_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error generating form instructions: {str(e)}", exc_info=True)
            return "Error generating form instructions"
            
    async def simulate_form_fill(self, form_data: Dict[str, Any], form_config: Dict[str, Any]) -> List[FormFillStatus]:
        """Simulate form filling without actually interacting with the browser"""
        self._fill_status_history = []  # Reset history
        
        # Analyze the form first
        analysis = await self.analyze_form_fields(form_data)
        
        # Simulate filling each field
        for field in analysis.fields:
            if self.config.simulation_mode:
                logger.info(f"SIMULATION: Would fill {field.field_name} with value {field.value}")
                self._add_status_entry(
                    field=field.field_name,
                    status="simulated",
                    value=field.value,
                    selector_used=field.selector_hint
                )
            else:
                # In real mode, we would actually fill the field
                self._add_status_entry(
                    field=field.field_name,
                    status="filled",
                    value=field.value,
                    selector_used=field.selector_hint
                )
        
        # Simulate form submission
        self._add_status_entry(
            field="submit",
            status="simulated" if self.config.simulation_mode else "clicked"
        )
        
        return self._fill_status_history 