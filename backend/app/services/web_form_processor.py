"""
Service for processing web-based forms and extracting field information.
"""

import logging
from typing import Dict, List, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
import re
from app.core.config import settings

logger = logging.getLogger(__name__)

class WebFormProcessor:
    """Service for processing web-based forms."""

    def __init__(self):
        """Initialize the web form processor."""
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def initialize(self):
        """Initialize the browser and page."""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self.page = await self.browser.new_page()
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    async def process_form(self, url: str) -> Dict[str, Any]:
        """Process a web form and extract field information."""
        try:
            if not self.page:
                await self.initialize()

            # Navigate to the form
            await self.page.goto(url, wait_until="networkidle")
            
            # Get the page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract form fields
            fields = []
            
            # Process input fields
            for input_field in soup.find_all(['input', 'select', 'textarea']):
                field_info = self._extract_field_info(input_field)
                if field_info:
                    fields.append(field_info)
            
            # Process labels and associate them with fields
            for label in soup.find_all('label'):
                field_info = self._process_label(label, fields)
                if field_info:
                    fields.append(field_info)
            
            # Extract form metadata
            form = soup.find('form')
            metadata = {
                'action': form.get('action', ''),
                'method': form.get('method', 'post').upper(),
                'enctype': form.get('enctype', ''),
                'fields': fields
            }
            
            return metadata
        except Exception as e:
            logger.error(f"Error processing web form: {str(e)}")
            raise

    def _extract_field_info(self, element) -> Optional[Dict[str, Any]]:
        """Extract information from a form field element."""
        try:
            field_type = element.name
            field_info = {
                'type': field_type,
                'name': element.get('name', ''),
                'id': element.get('id', ''),
                'required': element.get('required', False),
                'placeholder': element.get('placeholder', ''),
                'value': element.get('value', ''),
                'label': '',
                'options': []
            }
            
            # Handle different field types
            if field_type == 'select':
                field_info['options'] = [
                    {'value': option.get('value', ''), 'text': option.text.strip()}
                    for option in element.find_all('option')
                ]
            elif field_type == 'input':
                input_type = element.get('type', 'text')
                field_info['input_type'] = input_type
                
                # Handle special input types
                if input_type in ['checkbox', 'radio']:
                    field_info['checked'] = element.get('checked', False)
                elif input_type == 'file':
                    field_info['accept'] = element.get('accept', '')
            
            return field_info
        except Exception as e:
            logger.error(f"Error extracting field info: {str(e)}")
            return None

    def _process_label(self, label, fields: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Process a label element and associate it with fields."""
        try:
            label_text = label.text.strip()
            if not label_text:
                return None
                
            # Find associated field
            for field in fields:
                if field['id'] == label.get('for', '') or field['name'] == label.get('for', ''):
                    field['label'] = label_text
                    return None
            
            # If no associated field found, create a new field info
            return {
                'type': 'label',
                'text': label_text,
                'for': label.get('for', '')
            }
        except Exception as e:
            logger.error(f"Error processing label: {str(e)}")
            return None

    async def fill_form(self, url: str, field_values: Dict[str, Any]) -> bool:
        """Fill out a web form with provided values."""
        try:
            if not self.page:
                await self.initialize()

            # Navigate to the form
            await self.page.goto(url, wait_until="networkidle")
            
            # Fill each field
            for field_name, value in field_values.items():
                try:
                    # Try different selectors
                    selectors = [
                        f'input[name="{field_name}"]',
                        f'select[name="{field_name}"]',
                        f'textarea[name="{field_name}"]',
                        f'#{field_name}'
                    ]
                    
                    for selector in selectors:
                        element = await self.page.query_selector(selector)
                        if element:
                            # Handle different field types
                            field_type = await element.get_attribute('type')
                            
                            if field_type == 'checkbox':
                                if value:
                                    await element.check()
                            elif field_type == 'radio':
                                await element.check()
                            elif field_type == 'file':
                                # Handle file uploads
                                await element.set_input_files(value)
                            else:
                                await element.fill(str(value))
                            break
                except Exception as e:
                    logger.warning(f"Failed to fill field {field_name}: {str(e)}")
                    continue
            
            return True
        except Exception as e:
            logger.error(f"Error filling form: {str(e)}")
            return False

    async def submit_form(self, url: str, field_values: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a web form and return the response."""
        try:
            # Fill the form
            success = await this.fill_form(url, field_values)
            if not success:
                raise Exception("Failed to fill form")
            
            # Find and click submit button
            submit_button = await self.page.query_selector('button[type="submit"], input[type="submit"]')
            if submit_button:
                await submit_button.click()
                
                # Wait for navigation or response
                await this.page.wait_for_load_state('networkidle')
                
                # Get the response
                response = {
                    'url': this.page.url,
                    'content': await this.page.content(),
                    'status': 'success'
                }
                
                return response
            else:
                raise Exception("No submit button found")
        except Exception as e:
            logger.error(f"Error submitting form: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def cleanup(self):
        """Clean up resources."""
        try:
            if this.page:
                await this.page.close()
            if this.browser:
                await this.browser.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise 