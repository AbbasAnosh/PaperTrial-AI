"""
API router for field mapping operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from typing import Dict, Any, List, Optional
from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_client
from app.services.field_mapping_service import FieldMappingService
from app.models.field_mapping import FieldMapping, FieldMappingCreate, FieldMappingUpdate
from app.core.errors import ValidationError, NotFoundError, ProcessingError
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/field-mappings", tags=["field-mappings"])

@router.post("", response_model=FieldMapping, status_code=201)
async def create_field_mapping(
    field_mapping_create: FieldMappingCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new field mapping
    """
    try:
        supabase = get_supabase_client()
        field_mapping_service = FieldMappingService(supabase)
        field_mapping = await field_mapping_service.create_field_mapping(field_mapping_create, current_user["user_id"])
        return field_mapping
    except Exception as e:
        logger.error(f"Error creating field mapping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create field mapping"
        )

@router.get("/{field_mapping_id}", response_model=FieldMapping)
async def get_field_mapping(
    field_mapping_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a field mapping by ID
    """
    try:
        supabase = get_supabase_client()
        field_mapping_service = FieldMappingService(supabase)
        field_mapping = await field_mapping_service.get_field_mapping_by_id(field_mapping_id, current_user["user_id"])
        if not field_mapping:
            raise NotFoundError(f"Field mapping with ID {field_mapping_id} not found")
        return field_mapping
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting field mapping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get field mapping"
        )

@router.get("", response_model=List[FieldMapping])
async def get_user_field_mappings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all field mappings for the current user
    """
    try:
        supabase = get_supabase_client()
        field_mapping_service = FieldMappingService(supabase)
        field_mappings = await field_mapping_service.get_user_field_mappings(current_user["user_id"], skip=skip, limit=limit)
        return field_mappings
    except Exception as e:
        logger.error(f"Error getting user field mappings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get user field mappings"
        )

@router.put("/{field_mapping_id}", response_model=FieldMapping)
async def update_field_mapping(
    field_mapping_update: FieldMappingUpdate,
    field_mapping_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update a field mapping
    """
    try:
        supabase = get_supabase_client()
        field_mapping_service = FieldMappingService(supabase)
        field_mapping = await field_mapping_service.update_field_mapping(field_mapping_id, field_mapping_update, current_user["user_id"])
        if not field_mapping:
            raise NotFoundError(f"Field mapping with ID {field_mapping_id} not found")
        return field_mapping
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating field mapping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update field mapping"
        )

@router.delete("/{field_mapping_id}", status_code=204)
async def delete_field_mapping(
    field_mapping_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a field mapping
    """
    try:
        supabase = get_supabase_client()
        field_mapping_service = FieldMappingService(supabase)
        success = await field_mapping_service.delete_field_mapping(field_mapping_id, current_user["user_id"])
        if not success:
            raise NotFoundError(f"Field mapping with ID {field_mapping_id} not found")
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting field mapping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete field mapping"
        ) 