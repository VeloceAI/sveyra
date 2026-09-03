from unittest.mock import MagicMock

import pytest

from app.storage.deps import build_storage
from app.storage.gcs import GoogleCloudStorage
from app.storage.memory import InMemoryStorage


def test_build_storage_defaults_to_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.storage_backend", "memory")
    storage = build_storage()
    assert isinstance(storage, InMemoryStorage)


def test_build_storage_selects_gcs_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("google.cloud.storage.Client", lambda: MagicMock())
    monkeypatch.setattr("app.core.config.settings.storage_backend", "gcs")
    monkeypatch.setattr("app.core.config.settings.gcs_bucket_name", "prod-bucket")
    monkeypatch.setattr("app.core.config.settings.gcs_object_prefix", "media/")
    storage = build_storage()
    assert isinstance(storage, GoogleCloudStorage)
    assert storage._bucket_name == "prod-bucket"
    assert storage._object_prefix == "media/"


def test_build_storage_gcs_requires_bucket_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.storage_backend", "gcs")
    monkeypatch.setattr("app.core.config.settings.gcs_bucket_name", None)
    with pytest.raises(ValueError, match="GCS_BUCKET_NAME"):
        build_storage()
