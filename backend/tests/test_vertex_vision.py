import json

import httpx
import pytest

from app.core.config import settings
from app.vision.deps import build_vision
from app.vision.errors import VisionUnavailableError
from app.vision.vertex import VertexGeminiVision

JPEG = b"\xff\xd8\xffgarment-image"


def _success_response() -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "category": "blazer",
                                    "color": "navy",
                                    "pattern": "solid",
                                    "material": "wool",
                                    "silhouette": "tailored",
                                    "occasion_tags": ["work", "formal"],
                                    "category_confidence": 0.94,
                                    "color_confidence": 0.91,
                                }
                            )
                        }
                    ],
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 800, "candidatesTokenCount": 90},
    }


def test_vertex_gemini_sends_private_inline_image_and_parses_schema() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["authorization"] = request.headers["Authorization"]
        observed["body"] = json.loads(request.content)
        return httpx.Response(200, json=_success_response())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    vision = VertexGeminiVision(
        project="sveyra-test",
        client=client,
        access_token=lambda: "private-test-token",
    )

    analysis = vision.analyze_garment(JPEG)

    assert observed["url"] == (
        "https://aiplatform.googleapis.com/v1/projects/sveyra-test/locations/global/"
        "publishers/google/models/gemini-3.1-flash-lite:generateContent"
    )
    assert observed["authorization"] == "Bearer private-test-token"
    body = observed["body"]
    assert isinstance(body, dict)
    assert body["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "image/jpeg"
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseSchema"]["type"] == "OBJECT"
    assert analysis.category == "blazer"
    assert analysis.color == "navy"
    assert analysis.occasion_tags == ["work", "formal"]
    assert analysis.provider == "google-vertex"
    assert analysis.model == "gemini-3.1-flash-lite"
    assert analysis.input_tokens == 800
    assert analysis.output_tokens == 90


@pytest.mark.parametrize(
    "response",
    [
        {"candidates": []},
        {
            "candidates": [
                {"content": {"parts": [{"text": "not-json"}]}}
            ]
        },
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        **json.loads(
                                            _success_response()["candidates"][0]["content"][
                                                "parts"
                                            ][0]["text"]
                                        ),
                                        "category_confidence": 2,
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        },
    ],
)
def test_vertex_gemini_rejects_invalid_provider_output(response: dict) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=response))
    )
    vision = VertexGeminiVision(
        project="sveyra-test",
        client=client,
        access_token=lambda: "token",
    )

    with pytest.raises(VisionUnavailableError):
        vision.analyze_garment(JPEG)


def test_vertex_gemini_maps_http_failure_to_provider_error() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(429, json={"error": "quota"})
        )
    )
    vision = VertexGeminiVision(
        project="sveyra-test",
        client=client,
        access_token=lambda: "token",
    )

    with pytest.raises(VisionUnavailableError):
        vision.analyze_garment(JPEG)


def test_vertex_gemini_rejects_non_image_bytes_before_network() -> None:
    vision = VertexGeminiVision(
        project="sveyra-test",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: pytest.fail("network must not be called")
            )
        ),
        access_token=lambda: "token",
    )

    with pytest.raises(VisionUnavailableError):
        vision.analyze_garment(b"not-an-image")


def test_build_vertex_requires_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vision_backend", "vertex")
    monkeypatch.setattr(settings, "google_cloud_project", None)

    with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT"):
        build_vision()
