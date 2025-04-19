from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
from app.core.auth import get_current_user
from app.services.ai_service import AIService
from app.services.browser_automation import BrowserAutomationService
from app.services.submission_tracker import SubmissionTracker

router = APIRouter()
ai_service = AIService()
browser_service = BrowserAutomationService()
submission_tracker = SubmissionTracker()

@router.post("/process")
async def process_form(
    form_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    try:
        # Create submission record
        submission_id = await submission_tracker.create_submission(
            user_id=current_user["id"],
            form_data=form_data
        )
        
        # Analyze form with AI
        field_analysis = await ai_service.analyze_form_fields(form_data)
        await submission_tracker.add_submission_event(
            submission_id,
            "ai_analysis",
            {"analysis": field_analysis}
        )
        
        # Initialize browser automation
        await browser_service.initialize()
        
        # Fill form
        fill_result = await browser_service.fill_form(
            url=form_data.get("form_url"),
            form_data=form_data.get("fields", {})
        )
        
        if not fill_result["success"]:
            await submission_tracker.update_submission_status(
                submission_id,
                "failed",
                f"Form filling failed: {fill_result.get('error')}"
            )
            return JSONResponse(
                status_code=400,
                content={"error": "Form filling failed", "details": fill_result}
            )
        
        # Submit form
        submit_result = await browser_service.submit_form()
        
        if not submit_result["success"]:
            await submission_tracker.update_submission_status(
                submission_id,
                "failed",
                f"Form submission failed: {submit_result.get('error')}"
            )
            return JSONResponse(
                status_code=400,
                content={"error": "Form submission failed", "details": submit_result}
            )
        
        # Update submission status
        await submission_tracker.update_submission_status(
            submission_id,
            "completed",
            "Form successfully submitted"
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Form processed successfully",
                "submission_id": submission_id,
                "analysis": field_analysis
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await browser_service.close()

@router.get("/submissions")
async def get_submissions(current_user: dict = Depends(get_current_user)):
    try:
        submissions = await submission_tracker.get_submission_history(current_user["id"])
        return JSONResponse(
            status_code=200,
            content={"submissions": submissions}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        timeline = await submission_tracker.get_submission_timeline(submission_id)
        return JSONResponse(
            status_code=200,
            content={"timeline": timeline}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 