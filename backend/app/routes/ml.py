"""
API router for ML operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_client
from app.services.ml_service import MLService
from app.models.ml import ModelTrainingRequest, ModelEvaluationRequest, ModelSuggestionRequest
from app.core.errors import ValidationError, NotFoundError, ProcessingError
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["ml"])

@router.post("/train", response_model=Dict[str, Any])
async def train_model(
    request: ModelTrainingRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Train a new ML model
    """
    try:
        supabase = get_supabase_client()
        ml_service = MLService(supabase)
        result = await ml_service.train_model(
            workspace_id=request.workspace_id,
            model_name=request.model_name,
            training_data=request.training_data,
            user_id=current_user["user_id"]
        )
        return result
    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to train model"
        )

@router.post("/evaluate", response_model=Dict[str, Any])
async def evaluate_model(
    request: ModelEvaluationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Evaluate a trained ML model
    """
    try:
        supabase = get_supabase_client()
        ml_service = MLService(supabase)
        result = await ml_service.evaluate_model(
            model_id=request.model_id,
            test_data=request.test_data,
            user_id=current_user["user_id"]
        )
        return result
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error evaluating model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to evaluate model"
        )

@router.post("/suggest", response_model=List[Dict[str, Any]])
async def get_suggestions(
    request: ModelSuggestionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get field mapping suggestions from a trained model
    """
    try:
        supabase = get_supabase_client()
        ml_service = MLService(supabase)
        suggestions = await ml_service.get_suggestions(
            model_id=request.model_id,
            source_fields=request.source_fields,
            user_id=current_user["user_id"]
        )
        return suggestions
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get suggestions"
        )

@router.get("/models", response_model=List[Dict[str, Any]])
async def list_models(
    workspace_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all trained models for a workspace
    """
    try:
        supabase = get_supabase_client()
        ml_service = MLService(supabase)
        models = await ml_service.list_models(
            workspace_id=workspace_id,
            user_id=current_user["user_id"]
        )
        return models
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list models"
        )

@router.get("/models/{model_id}", response_model=Dict[str, Any])
async def get_model(
    model_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get details of a specific model
    """
    try:
        supabase = get_supabase_client()
        ml_service = MLService(supabase)
        model = await ml_service.get_model(
            model_id=model_id,
            user_id=current_user["user_id"]
        )
        if not model:
            raise NotFoundError(f"Model with ID {model_id} not found")
        return model
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get model"
        ) 