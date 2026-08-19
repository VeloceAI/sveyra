from fastapi import Request

from app.core.config import settings
from app.storage.gcs import GoogleCloudStorage
from app.storage.memory import InMemoryStorage
from app.storage.port import StoragePort


def build_storage() -> StoragePort:
    if settings.storage_backend == "gcs":
        if not settings.gcs_bucket_name:
            raise ValueError("GCS_BUCKET_NAME is required when STORAGE_BACKEND=gcs")
        return GoogleCloudStorage(
            bucket_name=settings.gcs_bucket_name,
            object_prefix=settings.gcs_object_prefix,
        )
    return InMemoryStorage()


def get_storage(request: Request) -> StoragePort:
    return request.app.state.storage
