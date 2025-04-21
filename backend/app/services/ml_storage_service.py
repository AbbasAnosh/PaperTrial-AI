import os
import shutil
from typing import Optional, BinaryIO
from uuid import UUID
import logging
from datetime import datetime
import json

from app.core.supabase import get_supabase
from app.core.errors import StorageError

logger = logging.getLogger(__name__)

class MLStorageService:
    def __init__(self, base_path: str = "models"):
        """Initialize storage service with base path for models."""
        self.base_path = base_path
        self.supabase = get_supabase()
        os.makedirs(base_path, exist_ok=True)

    def _get_model_path(self, workspace_id: UUID, model_name: str, version: str) -> str:
        """Get the path for a model file."""
        return os.path.join(
            self.base_path,
            str(workspace_id),
            f"{model_name}_{version}.pt"
        )

    def _get_model_metadata_path(self, workspace_id: UUID, model_name: str, version: str) -> str:
        """Get the path for a model's metadata file."""
        return os.path.join(
            self.base_path,
            str(workspace_id),
            f"{model_name}_{version}_metadata.json"
        )

    async def save_model(
        self,
        workspace_id: UUID,
        model_name: str,
        version: str,
        model_data: bytes,
        metadata: dict
    ) -> str:
        """Save a model and its metadata."""
        try:
            # Create workspace directory
            workspace_dir = os.path.join(self.base_path, str(workspace_id))
            os.makedirs(workspace_dir, exist_ok=True)

            # Save model file
            model_path = self._get_model_path(workspace_id, model_name, version)
            with open(model_path, "wb") as f:
                f.write(model_data)

            # Save metadata
            metadata_path = self._get_model_metadata_path(workspace_id, model_name, version)
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

            # Upload to cloud storage
            await self._upload_to_cloud(workspace_id, model_name, version, model_path, metadata_path)

            return model_path

        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            raise StorageError(f"Failed to save model: {str(e)}")

    async def load_model(
        self,
        workspace_id: UUID,
        model_name: str,
        version: str
    ) -> tuple[bytes, dict]:
        """Load a model and its metadata."""
        try:
            model_path = self._get_model_path(workspace_id, model_name, version)
            metadata_path = self._get_model_metadata_path(workspace_id, model_name, version)

            # Check if files exist locally
            if not (os.path.exists(model_path) and os.path.exists(metadata_path)):
                # Download from cloud storage
                await self._download_from_cloud(workspace_id, model_name, version)

            # Load model data
            with open(model_path, "rb") as f:
                model_data = f.read()

            # Load metadata
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            return model_data, metadata

        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise StorageError(f"Failed to load model: {str(e)}")

    async def delete_model(
        self,
        workspace_id: UUID,
        model_name: str,
        version: str
    ) -> None:
        """Delete a model and its metadata."""
        try:
            model_path = self._get_model_path(workspace_id, model_name, version)
            metadata_path = self._get_model_metadata_path(workspace_id, model_name, version)

            # Delete local files
            if os.path.exists(model_path):
                os.remove(model_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            # Delete from cloud storage
            await self._delete_from_cloud(workspace_id, model_name, version)

        except Exception as e:
            logger.error(f"Failed to delete model: {str(e)}")
            raise StorageError(f"Failed to delete model: {str(e)}")

    async def list_models(self, workspace_id: UUID) -> list[dict]:
        """List all models for a workspace."""
        try:
            workspace_dir = os.path.join(self.base_path, str(workspace_id))
            if not os.path.exists(workspace_dir):
                return []

            models = []
            for filename in os.listdir(workspace_dir):
                if filename.endswith("_metadata.json"):
                    metadata_path = os.path.join(workspace_dir, filename)
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        models.append(metadata)

            return models

        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            raise StorageError(f"Failed to list models: {str(e)}")

    async def _upload_to_cloud(
        self,
        workspace_id: UUID,
        model_name: str,
        version: str,
        model_path: str,
        metadata_path: str
    ) -> None:
        """Upload model files to cloud storage."""
        try:
            # Upload model file
            with open(model_path, "rb") as f:
                await this.supabase.storage.from_("models").upload(
                    f"{workspace_id}/{model_name}_{version}.pt",
                    f.read()
                )

            # Upload metadata
            with open(metadata_path, "rb") as f:
                await this.supabase.storage.from_("models").upload(
                    f"{workspace_id}/{model_name}_{version}_metadata.json",
                    f.read()
                )

        except Exception as e:
            logger.error(f"Failed to upload to cloud: {str(e)}")
            raise StorageError(f"Failed to upload to cloud: {str(e)}")

    async def _download_from_cloud(
        self,
        workspace_id: UUID,
        model_name: str,
        version: str
    ) -> None:
        """Download model files from cloud storage."""
        try:
            # Create workspace directory
            workspace_dir = os.path.join(self.base_path, str(workspace_id))
            os.makedirs(workspace_dir, exist_ok=True)

            # Download model file
            model_path = self._get_model_path(workspace_id, model_name, version)
            model_data = await this.supabase.storage.from_("models").download(
                f"{workspace_id}/{model_name}_{version}.pt"
            )
            with open(model_path, "wb") as f:
                f.write(model_data)

            # Download metadata
            metadata_path = self._get_model_metadata_path(workspace_id, model_name, version)
            metadata_data = await this.supabase.storage.from_("models").download(
                f"{workspace_id}/{model_name}_{version}_metadata.json"
            )
            with open(metadata_path, "wb") as f:
                f.write(metadata_data)

        except Exception as e:
            logger.error(f"Failed to download from cloud: {str(e)}")
            raise StorageError(f"Failed to download from cloud: {str(e)}")

    async def _delete_from_cloud(
        self,
        workspace_id: UUID,
        model_name: str,
        version: str
    ) -> None:
        """Delete model files from cloud storage."""
        try:
            # Delete model file
            await this.supabase.storage.from_("models").remove(
                f"{workspace_id}/{model_name}_{version}.pt"
            )

            # Delete metadata
            await this.supabase.storage.from_("models").remove(
                f"{workspace_id}/{model_name}_{version}_metadata.json"
            )

        except Exception as e:
            logger.error(f"Failed to delete from cloud: {str(e)}")
            raise StorageError(f"Failed to delete from cloud: {str(e)}") 