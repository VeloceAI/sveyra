"""Try-on providers and the vendor-neutrality guarantee."""

import base64
from pathlib import Path

import numpy as np
import pytest

from sveyra_human.providers import MockTryOnProvider, TryOnProvider, build_provider
from sveyra_human.providers.vertex.client import VertexClient, _extract_image
from sveyra_human.providers.vertex.config import VertexConfig
from sveyra_human.providers.vertex.tryon import VertexTryOnProvider


class FakeResponse:
    def __init__(self, predictions):
        self.predictions = predictions


class FakeEndpoint:
    def __init__(self, _name):
        self.calls = []

    def predict(self, instances):
        self.calls.append(instances)
        return FakeResponse([{"bytesBase64Encoded": base64.b64encode(b"generated").decode()}])


class FakeTransport:
    """Stands in for google.cloud.aiplatform without installing it."""

    def __init__(self):
        self.endpoint = None

    def Endpoint(self, name):  # noqa: N802 - matches the SDK's name
        self.endpoint = FakeEndpoint(name)
        return self.endpoint


# -- selection -----------------------------------------------------------


def test_the_default_provider_needs_no_credentials(monkeypatch) -> None:
    monkeypatch.delenv("TRYON_PROVIDER", raising=False)
    assert isinstance(build_provider(), MockTryOnProvider)


def test_the_provider_is_chosen_by_environment(monkeypatch) -> None:
    monkeypatch.setenv("TRYON_PROVIDER", "vertex")
    assert isinstance(build_provider(), VertexTryOnProvider)


def test_an_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        build_provider("midjourney")


def test_providers_satisfy_the_protocol() -> None:
    assert isinstance(MockTryOnProvider(), TryOnProvider)
    assert isinstance(VertexTryOnProvider(), TryOnProvider)


# -- configuration -------------------------------------------------------


def test_config_reads_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("VERTEX_PROJECT_ID", "sveyra-dev")
    monkeypatch.setenv("VERTEX_TRYON_MODEL", "projects/x/endpoints/y")
    monkeypatch.setenv("VERTEX_LOCATION", "europe-west4")
    config = VertexConfig.from_env()
    assert config.project_id == "sveyra-dev"
    assert config.location == "europe-west4"


def test_location_has_a_sensible_default(monkeypatch) -> None:
    monkeypatch.setenv("VERTEX_PROJECT_ID", "p")
    monkeypatch.setenv("VERTEX_TRYON_MODEL", "m")
    monkeypatch.delenv("VERTEX_LOCATION", raising=False)
    assert VertexConfig.from_env().location == "us-central1"


def test_missing_configuration_names_what_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("VERTEX_PROJECT_ID", raising=False)
    monkeypatch.delenv("VERTEX_TRYON_MODEL", raising=False)
    with pytest.raises(ValueError, match="VERTEX_PROJECT_ID"):
        VertexConfig.from_env()


def test_no_credential_is_ever_read_from_source() -> None:
    """Credentials must come from ADC or IAM, never from a literal."""
    source = Path(__file__).resolve().parents[1] / "src" / "sveyra_human" / "providers"
    for path in source.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "private_key" not in text, path
        assert "service_account.json" not in text, path


# -- transport -----------------------------------------------------------


def test_the_client_sends_both_images_and_returns_bytes() -> None:
    transport = FakeTransport()
    client = VertexClient(
        VertexConfig(project_id="p", location="l", model="m"), transport=transport
    )
    assert client.predict(b"person", b"garment") == b"generated"
    instance = transport.endpoint.calls[0][0]
    assert base64.b64decode(instance["personImage"]) == b"person"
    assert base64.b64decode(instance["productImage"]) == b"garment"


def test_the_provider_encodes_arrays_before_sending() -> None:
    transport = FakeTransport()
    provider = VertexTryOnProvider(
        client=VertexClient(
            VertexConfig(project_id="p", location="l", model="m"), transport=transport
        )
    )
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    assert provider.generate(image, image) == b"generated"
    sent = base64.b64decode(transport.endpoint.calls[0][0]["personImage"])
    assert sent.startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "response",
    [FakeResponse([]), FakeResponse(None), FakeResponse([{"unexpected": "shape"}])],
)
def test_an_unusable_response_raises_rather_than_returning_junk(response) -> None:
    with pytest.raises(RuntimeError):
        _extract_image(response)


def test_a_plain_base64_string_response_is_accepted() -> None:
    encoded = base64.b64encode(b"image-bytes").decode()
    assert _extract_image(FakeResponse([encoded])) == b"image-bytes"


# -- mock ----------------------------------------------------------------


def test_the_mock_is_deterministic_and_distinguishes_inputs() -> None:
    provider = MockTryOnProvider()
    assert provider.generate("p", "g") == provider.generate("p", "g")
    assert provider.generate("p", "g") != provider.generate("p", "other")
