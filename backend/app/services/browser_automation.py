from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging
import asyncio
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
import backoff
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.supabase_client import SupabaseClient

class BrowserAutomationService:
    def __init__(self):
        self.driver = None
        self.logger = logging.getLogger(__name__)
        self.wait_timeout = 30
        self.max_retries = 3
        self.retry_delay = 2
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.supabase = SupabaseClient()
        self.user_profile = None

    @backoff.on_exception(backoff.expo, WebDriverException, max_tries=3)
    async def initialize(self, user_id: Optional[str] = None):
        """Initialize the browser with retry logic"""
        try:
            if self.driver:
                await self.cleanup()

            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.wait_timeout)
            self.logger.info("Browser initialized successfully")
            
            if user_id:
                await self._load_user_profile(user_id)
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {str(e)}", exc_info=True)
            raise

    async def _load_user_profile(self, user_id: str):
        """Load user profile for autofill"""
        result = await self.supabase.table("user_profiles").select("*").eq("user_id", user_id).single().execute()
        if result.data:
            self.user_profile = result.data

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fill_form(self, url: str, form_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fill a form with the provided data and user profile
        """
        try:
            if not self.driver:
                await self.initialize()

            self.logger.info(f"Navigating to form URL: {url}")
            self.driver.get(url)
            
            # Wait for page load
            WebDriverWait(self.driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Take screenshot before filling
            before_screenshot = self._take_screenshot("before_fill")

            # Combine form data with user profile
            combined_data = self._combine_data(form_data, user_profile)
            
            # Track progress
            progress = {
                "total_fields": len(combined_data),
                "filled_fields": 0,
                "errors": [],
                "start_time": datetime.now().isoformat()
            }

            # Fill each field
            for field_name, value in combined_data.items():
                try:
                    await self._fill_field(field_name, value)
                    progress["filled_fields"] += 1
                except Exception as e:
                    error_msg = f"Error filling field {field_name}: {str(e)}"
                    self.logger.error(error_msg)
                    progress["errors"].append(error_msg)

            # Take screenshot after filling
            after_screenshot = self._take_screenshot("after_fill")

            progress.update({
                "end_time": datetime.now().isoformat(),
                "screenshots": {
                    "before": before_screenshot,
                    "after": after_screenshot
                }
            })

            return progress

        except Exception as e:
            self.logger.error(f"Failed to fill form: {str(e)}", exc_info=True)
            raise

    async def _fill_field(self, field_name: str, value: Any):
        """Fill a single form field with retry logic"""
        for attempt in range(self.max_retries):
            try:
                # Try different selectors
                selectors = [
                    (By.NAME, field_name),
                    (By.ID, field_name),
                    (By.CSS_SELECTOR, f"[name='{field_name}']"),
                    (By.XPATH, f"//*[@name='{field_name}']")
                ]

                element = None
                for by, selector in selectors:
                    try:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((by, selector))
                        )
                        if element:
                            break
                    except TimeoutException:
                        continue

                if not element:
                    raise ValueError(f"Field {field_name} not found")

                # Clear existing value
                element.clear()

                # Handle different input types
                input_type = element.get_attribute("type")
                if input_type == "checkbox":
                    if value:
                        element.click()
                elif input_type == "radio":
                    if value:
                        element.click()
                else:
                    element.send_keys(str(value))

                return

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                self.logger.warning(f"Retry {attempt + 1} for field {field_name}: {str(e)}")
                await asyncio.sleep(self.retry_delay)

    def _combine_data(self, form_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine form data with user profile data"""
        combined = form_data.copy()
        if user_profile:
            # Map user profile fields to form fields
            field_mapping = {
                "name": ["full_name", "name"],
                "email": ["email", "email_address"],
                "phone": ["phone", "phone_number", "telephone"],
                "address": ["address", "street_address"],
                "city": ["city", "town"],
                "state": ["state", "province"],
                "zip": ["zip", "postal_code", "zip_code"]
            }

            for profile_field, form_fields in field_mapping.items():
                if profile_field in user_profile:
                    for form_field in form_fields:
                        if form_field in combined and not combined[form_field]:
                            combined[form_field] = user_profile[profile_field]

        return combined

    def _take_screenshot(self, prefix: str) -> str:
        """Take a screenshot and return the file path"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            self.driver.save_screenshot(filepath)
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {str(e)}", exc_info=True)
            return ""

    async def submit_form(self, submit_button_selector: Optional[str] = None) -> bool:
        """Submit the form with retry logic"""
        try:
            if not self.driver:
                raise ValueError("Browser not initialized")

            # Try different submit button selectors
            selectors = [
                submit_button_selector,
                "input[type='submit']",
                "button[type='submit']",
                "//button[contains(text(), 'Submit')]",
                "//input[@value='Submit']"
            ]

            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    element.click()
                    return True
                except TimeoutException:
                    continue

            raise ValueError("Submit button not found")

        except Exception as e:
            self.logger.error(f"Failed to submit form: {str(e)}", exc_info=True)
            return False

    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.logger.info("Browser cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}", exc_info=True) 