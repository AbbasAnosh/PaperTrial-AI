"""
ML service for handling model training, evaluation, and suggestions.
"""

import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from app.models.ml import (
    ModelResponse,
    ModelEvaluationResponse,
    FieldSuggestion
)

logger = logging.getLogger(__name__)

class TextEncoder(nn.Module):
    """Text encoder using a pre-trained transformer model."""
    
    def __init__(self, model_name: str = "microsoft/deberta-v3-small"):
        super().__init__()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        
    def forward(self, texts: List[str]) -> torch.Tensor:
        """Encode a list of texts into embeddings."""
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt"
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
            
        return embeddings

class FieldMappingDataset(Dataset):
    """Dataset for field mapping training."""
    
    def __init__(self, texts: List[str], labels: List[str], tokenizer: AutoTokenizer):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        
    def __len__(self) -> int:
        return len(self.texts)
        
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        text = self.texts[idx]
        label = self.labels[idx]
        
        inputs = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=128,
            return_tensors="pt"
        )
        
        return {
            "input_ids": inputs["input_ids"].squeeze(),
            "attention_mask": inputs["attention_mask"].squeeze(),
            "labels": torch.tensor(self.label_to_id[label])
        }
        
    def label_to_id(self, label: str) -> int:
        """Convert label to integer ID."""
        if not hasattr(self, "_label_map"):
            self._label_map = {label: i for i, label in enumerate(set(self.labels))}
        return self._label_map[label]

class FieldMappingModel(nn.Module):
    """Model for field mapping using a transformer backbone."""
    
    def __init__(self, num_labels: int, model_name: str = "microsoft/deberta-v3-small"):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        self.classifier = nn.Linear(self.encoder.config.hidden_size, num_labels)
        
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        logits = self.classifier(outputs.last_hidden_state[:, 0, :])
        return logits

class MLService:
    """Service for handling ML operations."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.model_storage_path = os.getenv("MODEL_STORAGE_PATH", "models")
        os.makedirs(self.model_storage_path, exist_ok=True)
        
    async def train_model(
        self,
        workspace_id: str,
        model_name: str,
        training_data: List[Dict[str, Any]],
        user_id: str
    ) -> ModelResponse:
        """Train a new field mapping model."""
        try:
            # Prepare training data
            texts = [item["source_field"] for item in training_data]
            labels = [item["target_field"] for item in training_data]
            
            # Create dataset and dataloader
            dataset = FieldMappingDataset(texts, labels, AutoTokenizer.from_pretrained("microsoft/deberta-v3-small"))
            dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
            
            # Initialize model
            model = FieldMappingModel(num_labels=len(set(labels)))
            
            # Training loop
            optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
            criterion = nn.CrossEntropyLoss()
            
            model.train()
            for epoch in range(3):
                for batch in dataloader:
                    optimizer.zero_grad()
                    outputs = model(
                        input_ids=batch["input_ids"],
                        attention_mask=batch["attention_mask"]
                    )
                    loss = criterion(outputs, batch["labels"])
                    loss.backward()
                    optimizer.step()
            
            # Save model
            model_id = str(uuid.uuid4())
            model_path = os.path.join(self.model_storage_path, f"{model_id}.pt")
            torch.save(model.state_dict(), model_path)
            
            # Create model record
            model_data = {
                "id": model_id,
                "name": model_name,
                "workspace_id": workspace_id,
                "created_by": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metrics": {"accuracy": 0.0},  # Will be updated after evaluation
                "status": "trained",
                "version": "1.0.0"
            }
            
            # Save to database
            result = await self.supabase.table("ml_models").insert(model_data).execute()
            
            return ModelResponse(**model_data)
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise
            
    async def evaluate_model(
        self,
        model_id: str,
        test_data: List[Dict[str, Any]]
    ) -> ModelEvaluationResponse:
        """Evaluate a trained model."""
        try:
            # Load model
            model_path = os.path.join(self.model_storage_path, f"{model_id}.pt")
            model = FieldMappingModel(num_labels=len(set(item["target_field"] for item in test_data)))
            model.load_state_dict(torch.load(model_path))
            model.eval()
            
            # Prepare test data
            texts = [item["source_field"] for item in test_data]
            labels = [item["target_field"] for item in test_data]
            
            dataset = FieldMappingDataset(texts, labels, AutoTokenizer.from_pretrained("microsoft/deberta-v3-small"))
            dataloader = DataLoader(dataset, batch_size=16)
            
            # Evaluation
            all_preds = []
            all_labels = []
            
            with torch.no_grad():
                for batch in dataloader:
                    outputs = model(
                        input_ids=batch["input_ids"],
                        attention_mask=batch["attention_mask"]
                    )
                    preds = torch.argmax(outputs, dim=1)
                    all_preds.extend(preds.tolist())
                    all_labels.extend(batch["labels"].tolist())
            
            # Calculate metrics
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
            
            accuracy = accuracy_score(all_labels, all_preds)
            precision = precision_score(all_labels, all_preds, average="weighted")
            recall = recall_score(all_labels, all_preds, average="weighted")
            f1 = f1_score(all_labels, all_preds, average="weighted")
            conf_matrix = confusion_matrix(all_labels, all_preds).tolist()
            
            # Update model metrics in database
            await self.supabase.table("ml_models").update({
                "metrics": {
                    "accuracy": accuracy,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1
                }
            }).eq("id", model_id).execute()
            
            return ModelEvaluationResponse(
                model_id=model_id,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                confusion_matrix=conf_matrix,
                evaluation_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error evaluating model: {str(e)}")
            raise
            
    async def get_suggestions(
        self,
        model_id: str,
        source_fields: List[str]
    ) -> List[FieldSuggestion]:
        """Get field mapping suggestions from a trained model."""
        try:
            # Load model
            model_path = os.path.join(self.model_storage_path, f"{model_id}.pt")
            model = FieldMappingModel(num_labels=len(source_fields))
            model.load_state_dict(torch.load(model_path))
            model.eval()
            
            # Prepare input
            tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-small")
            inputs = tokenizer(
                source_fields,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt"
            )
            
            # Get predictions
            with torch.no_grad():
                outputs = model(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs["attention_mask"]
                )
                probs = torch.softmax(outputs, dim=1)
                preds = torch.argmax(probs, dim=1)
                confidences = torch.max(probs, dim=1)[0]
            
            # Create suggestions
            suggestions = []
            for i, (source_field, pred, conf) in enumerate(zip(source_fields, preds, confidences)):
                suggestions.append(
                    FieldSuggestion(
                        source_field=source_field,
                        target_field=source_fields[pred.item()],
                        confidence=conf.item(),
                        context={"model_id": model_id}
                    )
                )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting suggestions: {str(e)}")
            raise
            
    async def list_models(self, workspace_id: str) -> List[ModelResponse]:
        """List all trained models for a workspace."""
        try:
            result = await self.supabase.table("ml_models").select("*").eq("workspace_id", workspace_id).execute()
            return [ModelResponse(**model) for model in result.data]
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            raise
            
    async def get_model(self, model_id: str) -> ModelResponse:
        """Get details of a specific model."""
        try:
            result = await self.supabase.table("ml_models").select("*").eq("id", model_id).execute()
            if not result.data:
                raise ValueError(f"Model {model_id} not found")
            return ModelResponse(**result.data[0])
        except Exception as e:
            logger.error(f"Error getting model: {str(e)}")
            raise 