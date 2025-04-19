from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Browser, Page, Locator
import asyncio
from datetime import datetime
from app.core.supabase_client import SupabaseClient

class BrowserAutomationService:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.supabase = SupabaseClient()
        self.user_profile = None

    async def initialize(self, user_id: Optional[str] = None):
        """Initialize the browser automation service and load user profile"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        if user_id:
            await self._load_user_profile(user_id)

    async def _load_user_profile(self, user_id: str):
        """Load user profile for autofill"""
        result = await self.supabase.table("user_profiles").select("*").eq("user_id", user_id).single().execute()
        if result.data:
            self.user_profile = result.data

    async def fill_form(self, url: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a form with the provided data and user profile"""
        try:
            await self.page.goto(url)
            
            # Track form filling progress
            progress = {
                "start_time": datetime.now().isoformat(),
                "steps": [],
                "status": "in_progress"
            }
            
            # Combine form data with user profile
            combined_data = self._combine_with_profile(form_data)
            
            for field, value in combined_data.items():
                # Try different selectors
                selectors = [
                    f'input[name="{field}"]',
                    f'input[id="{field}"]',
                    f'textarea[name="{field}"]',
                    f'textarea[id="{field}"]',
                    f'select[name="{field}"]',
                    f'select[id="{field}"]'
                ]
                
                for selector in selectors:
                    if await self.page.locator(selector).count() > 0:
                        element = self.page.locator(selector)
                        await self._fill_element(element, value)
                        
                        progress["steps"].append({
                            "field": field,
                            "status": "filled",
                            "timestamp": datetime.now().isoformat(),
                            "value_source": "user_profile" if field in self.user_profile else "form_data"
                        })
                        break
            
            progress["status"] = "completed"
            progress["end_time"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "progress": progress
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "progress": progress
            }

    def _combine_with_profile(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine form data with user profile data"""
        if not self.user_profile:
            return form_data
            
        combined = form_data.copy()
        for field, value in self.user_profile.items():
            if field not in combined:
                combined[field] = value
        return combined

    async def _fill_element(self, element: Locator, value: Any):
        """Fill a form element with the appropriate method based on its type"""
        element_type = await element.get_attribute("type")
        
        if element_type == "checkbox":
            if value:
                await element.check()
        elif element_type == "radio":
            await element.check()
        elif element_type == "select":
            await element.select_option(value)
        else:
            await element.fill(str(value))

    async def submit_form(self) -> Dict[str, Any]:
        """Submit the form and track the submission"""
        try:
            # Try to find and click submit button
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Send")',
                'button:has-text("Next")',
                'button:has-text("Continue")'
            ]
            
            for selector in submit_selectors:
                if await self.page.locator(selector).count() > 0:
                    await self.page.click(selector)
                    break
            
            # Wait for navigation or form submission
            await self.page.wait_for_load_state("networkidle")
            
            # Capture submission result
            submission_result = {
                "success": True,
                "submission_time": datetime.now().isoformat(),
                "final_url": self.page.url,
                "page_title": await self.page.title()
            }
            
            return submission_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def close(self):
        """Close the browser and cleanup"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close() 