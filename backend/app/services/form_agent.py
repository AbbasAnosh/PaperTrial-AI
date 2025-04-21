from typing import Dict, Any, Optional, List, Tuple
import json
import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page, Locator, TimeoutError as PlaywrightTimeoutError
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from app.services.ai_service import AIService, FormFillStatus
import logging
from datetime import datetime
import re
import base64
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FormAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ai_service = AIService()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        self.form_configs = {}
        self.load_form_configs()
        self.simulation_mode = self.config.get("simulation_mode", False)
        self.debug_mode = self.config.get("debug_mode", False)
        self.screenshot_dir = Path("temp/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._fill_status_history: List[FormFillStatus] = []
        self._current_step_index = 0
        self._form_type = None

    def load_form_configs(self):
        """Load all form configurations from the config directory"""
        config_dir = Path("backend/app/config/forms")
        for config_file in config_dir.glob("*.json"):
            with open(config_file) as f:
                form_id = config_file.stem
                self.form_configs[form_id] = json.load(f)

    async def initialize(self):
        """Initialize the browser automation service"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=not self.debug_mode,
            slow_mo=100 if self.debug_mode else 0
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir="temp/videos" if self.debug_mode else None
        )
        self.page = await self.context.new_page()
        
        # Set up event listeners for debugging
        if self.debug_mode:
            self.page.on("console", lambda msg: logger.debug(f"Browser console: {msg.text}"))
            self.page.on("pageerror", lambda err: logger.error(f"Browser error: {err}"))

    async def close(self):
        """Close the browser and cleanup"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

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
    async def _wait_for_element(self, selector: str, timeout: int = 10000) -> Locator:
        """Wait for an element to be visible with retry logic"""
        try:
            return await self.page.wait_for_selector(selector, timeout=timeout)
        except PlaywrightTimeoutError:
            logger.error(f"Timeout waiting for element: {selector}")
            raise

    async def _capture_screenshot(self, name: str) -> str:
        """Capture a screenshot of the current page"""
        if not self.debug_mode and not self.simulation_mode:
            return ""
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.screenshot_dir / f"{name}_{timestamp}.png"
        await self.page.screenshot(path=str(screenshot_path))
        logger.info(f"Screenshot saved: {screenshot_path}")
        return str(screenshot_path)

    async def process_form(self, form_id: str, user_data: Dict[str, Any], documents: Dict[str, str]) -> Dict[str, Any]:
        """Process a form using the provided configuration and data"""
        self._fill_status_history = []  # Reset history
        self._current_step_index = 0
        
        try:
            if form_id not in self.form_configs:
                raise ValueError(f"Form configuration not found: {form_id}")

            form_config = self.form_configs[form_id]
            
            # Classify form type using AI
            form_analysis = await this.ai_service.analyze_form_fields(user_data)
            self._form_type = form_analysis.form_type
            
            # Initialize browser if not in simulation mode
            if not self.simulation_mode:
                await this.initialize()
                await this.page.goto(form_config["base_url"])
            
            results = {
                "form_id": form_id,
                "form_type": self._form_type,
                "start_time": datetime.utcnow().isoformat(),
                "pages": [],
                "status": "in_progress"
            }

            # Process each page
            for i, page_config in enumerate(form_config["pages"]):
                self._current_step_index = i
                page_result = await this._process_page(page_config, user_data, documents)
                results["pages"].append(page_result)

                if page_result["status"] != "success":
                    results["status"] = "failed"
                    break

            # Check success criteria
            if results["status"] == "in_progress":
                success = await this._check_success_criteria(form_config["success_criteria"])
                results["status"] = "success" if success else "failed"

            # Capture final state
            results["end_time"] = datetime.utcnow().isoformat()
            results["screenshot"] = await this._capture_screenshot("final")
            results["fill_history"] = [status.dict() for status in this._fill_status_history]

            return results

        except Exception as e:
            logger.error(f"Error processing form: {str(e)}", exc_info=True)
            this._add_status_entry("form", "error", error=str(e))
            return {
                "form_id": form_id,
                "status": "failed",
                "error": str(e),
                "end_time": datetime.utcnow().isoformat(),
                "fill_history": [status.dict() for status in this._fill_status_history]
            }
        finally:
            if not self.simulation_mode:
                await this.close()

    async def _process_page(self, page_config: Dict[str, Any], user_data: Dict[str, Any], documents: Dict[str, str]) -> Dict[str, Any]:
        """Process a single page of the form"""
        page_result = {
            "name": page_config["name"],
            "start_time": datetime.utcnow().isoformat(),
            "fields": [],
            "status": "in_progress"
        }

        try:
            # Wait for the page to load
            if not self.simulation_mode:
                await this.page.wait_for_url(lambda url: page_config["url_contains"] in url)
                await this._capture_screenshot(f"page_{page_config['name']}")

            # Process each field
            for selector, field_config in page_config["fields"].items():
                field_result = await this._process_field(selector, field_config, user_data, documents)
                page_result["fields"].append(field_result)

                if field_result["status"] != "success":
                    page_result["status"] = "failed"
                    return page_result

            # Execute page actions
            for action in page_config.get("actions", []):
                action_result = await this._execute_action(action)
                if action_result["status"] != "success":
                    page_result["status"] = "failed"
                    page_result["error"] = action_result.get("error")
                    return page_result

            page_result["status"] = "success"
            return page_result

        except Exception as e:
            logger.error(f"Error processing page: {str(e)}", exc_info=True)
            page_result["status"] = "failed"
            page_result["error"] = str(e)
            return page_result

    async def _process_field(self, selector: str, field_config: Dict[str, Any], user_data: Dict[str, Any], documents: Dict[str, str]) -> Dict[str, Any]:
        """Process a single form field"""
        field_result = {
            "selector": selector,
            "type": field_config["type"],
            "status": "in_progress"
        }

        try:
            # Get the value using template
            value = await this.ai_service.resolve_template(field_config["value"], user_data, documents)
            
            if self.simulation_mode:
                logger.info(f"SIMULATION: Would fill {selector} with value {value}")
                this._add_status_entry(
                    field=selector,
                    status="simulated",
                    value=value,
                    selector_used=selector
                )
                field_result["status"] = "success"
                return field_result
            
            # Wait for the field to be visible
            element = await this._wait_for_element(selector)
            
            # Get additional field attributes for better matching
            label_text = await element.evaluate("el => el.labels?.[0]?.innerText || ''")
            placeholder = await element.get_attribute("placeholder") or ""
            aria_label = await element.get_attribute("aria-label") or ""
            
            # Handle different field types
            if field_config["type"] == "text":
                await element.fill(value)
            elif field_config["type"] == "select":
                await element.select_option(value)
            elif field_config["type"] == "file":
                # Handle file uploads
                if value.startswith("data:"):
                    # Handle base64 encoded files
                    file_data = value.split(",")[1]
                    file_content = base64.b64decode(file_data)
                    temp_path = f"temp/uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{field_config.get('filename', 'file')}"
                    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                    with open(temp_path, "wb") as f:
                        f.write(file_content)
                    await element.set_input_files(temp_path)
                else:
                    # Handle file paths
                    await element.set_input_files(value)
            elif field_config["type"] == "checkbox":
                if value.lower() in ["true", "yes", "1"]:
                    await element.check()
                else:
                    await element.uncheck()
            elif field_config["type"] == "radio":
                await element.check()
            
            # Add status entry
            this._add_status_entry(
                field=selector,
                status="filled",
                value=value,
                selector_used=selector
            )
            
            field_result["status"] = "success"
            return field_result

        except Exception as e:
            logger.error(f"Error processing field: {str(e)}", exc_info=True)
            field_result["status"] = "failed"
            field_result["error"] = str(e)
            this._add_status_entry(
                field=selector,
                status="error",
                error=str(e),
                selector_used=selector
            )
            return field_result

    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a page action"""
        action_result = {
            "type": action["type"],
            "status": "in_progress"
        }
        
        try:
            if self.simulation_mode:
                logger.info(f"SIMULATION: Would execute action {action['type']}")
                this._add_status_entry(
                    field=f"action_{action['type']}",
                    status="simulated",
                    value=action.get("selector", "")
                )
                action_result["status"] = "success"
                return action_result
                
            if action["type"] == "click":
                element = await this._wait_for_element(action["selector"])
                await element.click()
                this._add_status_entry(
                    field=f"action_{action['type']}",
                    status="clicked",
                    value=action["selector"]
                )
            elif action["type"] == "wait":
                await this.page.wait_for_timeout(action["timeout"])
                this._add_status_entry(
                    field=f"action_{action['type']}",
                    status="waited",
                    value=str(action["timeout"])
                )
            elif action["type"] == "navigate":
                await this.page.goto(action["url"])
                this._add_status_entry(
                    field=f"action_{action['type']}",
                    status="navigated",
                    value=action["url"]
                )
            
            action_result["status"] = "success"
            return action_result
            
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}", exc_info=True)
            action_result["status"] = "failed"
            action_result["error"] = str(e)
            this._add_status_entry(
                field=f"action_{action['type']}",
                status="error",
                error=str(e),
                value=action.get("selector", "")
            )
            return action_result

    async def _check_success_criteria(self, criteria: Dict[str, Any]) -> bool:
        """Check if the form submission was successful"""
        try:
            if self.simulation_mode:
                return True
                
            if "url_contains" in criteria:
                current_url = this.page.url
                if criteria["url_contains"] not in current_url:
                    this._add_status_entry(
                        field="success_check",
                        status="failed",
                        error=f"URL does not contain {criteria['url_contains']}"
                    )
                    return False

            if "element_exists" in criteria:
                element = await this.page.query_selector(criteria["element_exists"])
                if not element:
                    this._add_status_entry(
                        field="success_check",
                        status="failed",
                        error=f"Element {criteria['element_exists']} not found"
                    )
                    return False
                
            this._add_status_entry(
                field="success_check",
                status="success"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error checking success criteria: {str(e)}", exc_info=True)
            this._add_status_entry(
                field="success_check",
                status="error",
                error=str(e)
            )
            return False 