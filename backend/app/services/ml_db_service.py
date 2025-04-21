from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime

from app.core.supabase import get_supabase
from app.models.ml import (
    MLModel, MLModelCreate, MLModelEvaluation, MLModelEvaluationCreate,
    MLTrainingData, MLTrainingDataCreate
)
from app.core.errors import DatabaseError

logger = logging.getLogger(__name__)

class MLDatabaseService:
    def __init__(self):
        self.supabase = get_supabase()

    async def create_model(self, model: MLModelCreate, user_id: UUID) -> MLModel:
        """Create a new ML model."""
        try:
            data = model.dict()
            data["created_by"] = str(user_id)
            
            response = await self.supabase.table("ml_models").insert(data).execute()
            return MLModel(**response.data[0])
        except Exception as e:
            logger.error(f"Failed to create ML model: {str(e)}")
            raise DatabaseError(f"Failed to create ML model: {str(e)}")

    async def get_model(self, model_id: UUID) -> Optional[MLModel]:
        """Get an ML model by ID."""
        try:
            response = await self.supabase.table("ml_models").select("*").eq("id", str(model_id)).execute()
            if not response.data:
                return None
            return MLModel(**response.data[0])
        except Exception as e:
            logger.error(f"Failed to get ML model: {str(e)}")
            raise DatabaseError(f"Failed to get ML model: {str(e)}")

    async def list_workspace_models(self, workspace_id: UUID) -> List[MLModel]:
        """List all ML models for a workspace."""
        try:
            response = await self.supabase.table("ml_models").select("*").eq("workspace_id", str(workspace_id)).execute()
            return [MLModel(**model) for model in response.data]
        except Exception as e:
            logger.error(f"Failed to list workspace models: {str(e)}")
            raise DatabaseError(f"Failed to list workspace models: {str(e)}")

    async def update_model(self, model_id: UUID, updates: Dict[str, Any]) -> MLModel:
        """Update an ML model."""
        try:
            response = await self.supabase.table("ml_models").update(updates).eq("id", str(model_id)).execute()
            return MLModel(**response.data[0])
        except Exception as e:
            logger.error(f"Failed to update ML model: {str(e)}")
            raise DatabaseError(f"Failed to update ML model: {str(e)}")

    async def create_training_data(self, data: MLTrainingDataCreate, user_id: UUID) -> MLTrainingData:
        """Create new training data."""
        try:
            data_dict = data.dict()
            data_dict["created_by"] = str(user_id)
            
            response = await self.supabase.table("ml_training_data").insert(data_dict).execute()
            return MLTrainingData(**response.data[0])
        except Exception as e:
            logger.error(f"Failed to create training data: {str(e)}")
            raise DatabaseError(f"Failed to create training data: {str(e)}")

    async def get_model_training_data(self, model_id: UUID) -> List[MLTrainingData]:
        """Get all training data for a model."""
        try:
            response = await self.supabase.table("ml_training_data").select("*").eq("model_id", str(model_id)).execute()
            return [MLTrainingData(**data) for data in response.data]
        except Exception as e:
            logger.error(f"Failed to get model training data: {str(e)}")
            raise DatabaseError(f"Failed to get model training data: {str(e)}")

    async def create_evaluation(self, evaluation: MLModelEvaluationCreate, user_id: UUID) -> MLModelEvaluation:
        """Create a new model evaluation."""
        try:
            data = evaluation.dict()
            data["created_by"] = str(user_id)
            data["evaluation_date"] = datetime.utcnow().isoformat()
            
            response = await self.supabase.table("ml_model_evaluations").insert(data).execute()
            return MLModelEvaluation(**response.data[0])
        except Exception as e:
            logger.error(f"Failed to create model evaluation: {str(e)}")
            raise DatabaseError(f"Failed to create model evaluation: {str(e)}")

    async def get_model_evaluations(self, model_id: UUID) -> List[MLModelEvaluation]:
        """Get all evaluations for a model."""
        try:
            response = await self.supabase.table("ml_model_evaluations").select("*").eq("model_id", str(model_id)).execute()
            return [MLModelEvaluation(**eval_data) for eval_data in response.data]
        except Exception as e:
            logger.error(f"Failed to get model evaluations: {str(e)}")
            raise DatabaseError(f"Failed to get model evaluations: {str(e)}")

    async def get_latest_evaluation(self, model_id: UUID) -> Optional[MLModelEvaluation]:
        """Get the latest evaluation for a model."""
        try:
            response = await self.supabase.table("ml_model_evaluations").select("*").eq("model_id", str(model_id)).order("evaluation_date", desc=True).limit(1).execute()
            if not response.data:
                return None
            return MLModelEvaluation(**response.data[0])
        except Exception as e:
            logger.error(f"Failed to get latest model evaluation: {str(e)}")
            raise DatabaseError(f"Failed to get latest model evaluation: {str(e)}") 