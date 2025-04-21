import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import json
import numpy as np
import torch
from torch import nn
from transformers import AutoTokenizer, AutoModel
import joblib
import os
import tempfile

from app.models.field_mapping import MLTrainingData, MLSuggestion, MLModelMetadata
from app.core.supabase import get_supabase
from app.core.errors import ValidationError

logger = logging.getLogger(__name__)

class TextEncoder(nn.Module):
    def __init__(self, model_name: str = "microsoft/deberta-v3-small"):
        super().__init__()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)

    def encode(self, texts: List[str]) -> torch.Tensor:
        encodings = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors='pt'
        )
        encodings = {k: v.to(self.device) for k, v in encodings.items()}
        
        with torch.no_grad():
            outputs = self.model(**encodings)
            embeddings = outputs.last_hidden_state[:, 0, :]  # Use [CLS] token embedding
            return embeddings

class MLMappingService:
    def __init__(self, workspace_id: UUID):
        self.workspace_id = workspace_id
        self.supabase = get_supabase()
        self._training_data_cache = None
        self._model_metadata_cache = None
        self._encoder = TextEncoder()
        self._model = None
        self._model_version = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    async def get_training_data(self, refresh_cache: bool = False) -> List[MLTrainingData]:
        """Get all training data for the workspace."""
        if self._training_data_cache is None or refresh_cache:
            response = await self.supabase.table("ml_training_data").select("*").eq(
                "workspace_id", str(self.workspace_id)
            ).execute()
            
            self._training_data_cache = [MLTrainingData(**data) for data in response.data]
        
        return self._training_data_cache

    async def get_model_metadata(self, refresh_cache: bool = False) -> List[MLModelMetadata]:
        """Get all ML model metadata for the workspace."""
        if self._model_metadata_cache is None or refresh_cache:
            response = await self.supabase.table("ml_model_metadata").select("*").eq(
                "workspace_id", str(self.workspace_id)
            ).eq("is_active", True).execute()
            
            self._model_metadata_cache = [MLModelMetadata(**data) for data in response.data]
        
        return self._model_metadata_cache

    async def add_training_data(self, data: MLTrainingData) -> MLTrainingData:
        """Add new training data."""
        response = await self.supabase.table("ml_training_data").insert(
            data.dict(exclude={'id'})
        ).execute()
        
        self._training_data_cache = None  # Invalidate cache
        return MLTrainingData(**response.data[0])

    async def add_model_metadata(self, metadata: MLModelMetadata) -> MLModelMetadata:
        """Add new model metadata."""
        response = await self.supabase.table("ml_model_metadata").insert(
            metadata.dict(exclude={'id'})
        ).execute()
        
        self._model_metadata_cache = None  # Invalidate cache
        return MLModelMetadata(**response.data[0])

    async def train_model(self, model_name: str = "field_mapping_model") -> MLModelMetadata:
        """Train a new ML model for field mapping."""
        # Get training data
        training_data = await self.get_training_data(refresh_cache=True)
        if not training_data:
            raise ValidationError("No training data available")
        
        # Extract features
        source_fields = [data.source_field for data in training_data]
        target_fields = [data.target_field for data in training_data]
        document_types = [data.document_type or "" for data in training_data]
        
        # Encode source fields using transformer
        source_embeddings = self._encoder.encode(source_fields)
        
        # Create a simple similarity-based model
        self._model = {
            "source_embeddings": source_embeddings,
            "source_fields": source_fields,
            "target_fields": target_fields,
            "document_types": document_types
        }
        
        # Create model metadata
        model_version = "1.0.0"
        metadata = MLModelMetadata(
            workspace_id=self.workspace_id,
            model_name=model_name,
            version=model_version,
            description="Transformer-based field mapping model",
            features=["source_field", "document_type"],
            hyperparameters={
                "model": "deberta-v3-small",
                "max_length": 128
            },
            performance_metrics={
                "accuracy": 0.0  # Would be calculated in a real implementation
            }
        )
        
        # Save model metadata
        await self.add_model_metadata(metadata)
        
        # Save model to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pt") as tmp:
            torch.save(self._model, tmp.name)
            
            # Upload model to Supabase storage
            with open(tmp.name, "rb") as f:
                await self.supabase.storage.from_("models").upload(
                    f"{self.workspace_id}/{model_name}_{model_version}.pt",
                    f.read()
                )
        
        # Clean up temporary file
        os.unlink(tmp.name)
        
        self._model_version = model_version
        return metadata

    async def load_model(self, model_name: str = "field_mapping_model", version: str = "1.0.0") -> bool:
        """Load a trained ML model."""
        try:
            # Download model from Supabase storage
            response = await self.supabase.storage.from_("models").download(
                f"{self.workspace_id}/{model_name}_{version}.pt"
            )
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pt") as tmp:
                tmp.write(response)
                tmp_path = tmp.name
            
            # Load model
            self._model = torch.load(tmp_path)
            
            # Clean up temporary file
            os.unlink(tmp_path)
            
            self._model_version = version
            return True
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False

    async def generate_suggestions(self, source_field: str, context: Dict[str, Any]) -> List[MLSuggestion]:
        """Generate ML-based suggestions for field mapping."""
        if not self._model:
            # Try to load the latest model
            metadata_list = await this.get_model_metadata()
            if not metadata_list:
                return []
            
            latest_model = max(metadata_list, key=lambda m: m.version)
            success = await this.load_model(latest_model.model_name, latest_model.version)
            if not success:
                return []
        
        # Encode source field
        source_embedding = this._encoder.encode([source_field])
        
        # Calculate similarities using cosine similarity
        similarities = torch.nn.functional.cosine_similarity(
            source_embedding.unsqueeze(1),
            this._model["source_embeddings"].unsqueeze(0),
            dim=2
        )[0]
        
        # Get top 5 similar fields
        top_indices = torch.argsort(similarities, descending=True)[:5]
        
        suggestions = []
        for idx in top_indices:
            confidence = float(similarities[idx])
            if confidence > 0.3:  # Minimum confidence threshold
                suggestions.append(MLSuggestion(
                    field=self._model["target_fields"][idx],
                    confidence=confidence,
                    explanation=f"Based on similarity to '{self._model['source_fields'][idx]}'",
                    model_version=self._model_version,
                    features_used=["source_field"]
                ))
        
        return suggestions

    async def evaluate_model(self, test_data: List[MLTrainingData]) -> Dict[str, float]:
        """Evaluate model performance on test data."""
        if not self._model:
            return {"error": "No model loaded"}
        
        correct = 0
        total = len(test_data)
        
        for data in test_data:
            suggestions = await this.generate_suggestions(data.source_field, data.context or {})
            if suggestions and suggestions[0].field == data.target_field:
                correct += 1
        
        accuracy = correct / total if total > 0 else 0
        
        return {
            "accuracy": accuracy,
            "total_samples": total,
            "correct_predictions": correct
        } 