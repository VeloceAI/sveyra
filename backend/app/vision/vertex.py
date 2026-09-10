import base64
import json
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import google.auth
import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.vision.errors import VisionUnavailableError
from app.vision.port import GarmentAnalysis, VisionPort

_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

_CATEGORIES = [
    "shirt",
    "blouse",
    "t-shirt",
    "tank top",
    "sweater",
    "cardigan",
    "hoodie",
    "jacket",
    "blazer",
    "coat",
    "dress",
    "jumpsuit",
    "trousers",
    "jeans",
    "leggings",
    "shorts",
    "skirt",
    "shoes",
    "sneakers",
    "boots",
    "sandals",
    "heels",
    "flats",
    "bag",
    "belt",
    "scarf",
    "hat",
    "jewelry",
    "other",
]

_COLORS = [
    "black",
    "white",
    "gray",
    "navy",
    "blue",
    "red",
    "pink",
    "purple",
    "green",
    "yellow",
    "orange",
    "brown",
    "beige",
    "cream",
    "metallic",
    "multicolor",
    "unknown",
]

_OCCASIONS = [
    "casual",
    "work",
    "formal",
    "party",
    "date",
    "travel",
    "sport",
    "outdoor",
]

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "category": {"type": "STRING", "enum": _CATEGORIES},
        "color": {"type": "STRING", "enum": _COLORS},
        "pattern": {
            "type": "STRING",
            "description": "Short visible pattern name, or unknown.",
        },
        "material": {
            "type": "STRING",
            "description": "Likely material from visible evidence, or unknown.",
        },
        "silhouette": {
            "type": "STRING",
            "description": "Short fit or silhouette description, or unknown.",
        },
        "occasion_tags": {
            "type": "ARRAY",
            "items": {"type": "STRING", "enum": _OCCASIONS},
            "maxItems": 4,
        },
        "category_confidence": {"type": "NUMBER", "minimum": 0, "maximum": 1},
        "color_confidence": {"type": "NUMBER", "minimum": 0, "maximum": 1},
    },
    "required": [
        "category",
        "color",
        "pattern",
        "material",
        "silhouette",
        "occasion_tags",
        "category_confidence",
        "color_confidence",
    ],
}


class _GarmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(max_length=100)
    color: str = Field(max_length=100)
    pattern: str = Field(max_length=100)
    material: str = Field(max_length=100)
    silhouette: str = Field(max_length=100)
    occasion_tags: list[str] = Field(max_length=4)
    category_confidence: float = Field(ge=0, le=1)
    color_confidence: float = Field(ge=0, le=1)


def _image_mime_type(image: bytes) -> str:
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "image/webp"
    raise VisionUnavailableError


def _default_access_token() -> str:
    try:
        credentials, _project = google.auth.default(scopes=[_CLOUD_PLATFORM_SCOPE])
        if not credentials.valid:
            credentials.refresh(GoogleAuthRequest())
        token = credentials.token
    except Exception as exc:
        raise VisionUnavailableError from exc
    if not token:
        raise VisionUnavailableError
    return token


class VertexGeminiVision(VisionPort):
    """Managed Gemini garment understanding through the Vertex publisher endpoint."""

    def __init__(
        self,
        *,
        project: str,
        location: str = "global",
        model: str = "gemini-3.1-flash-lite",
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
        access_token: Callable[[], str] | None = None,
    ) -> None:
        if not project.strip() or not location.strip() or not model.strip():
            raise ValueError("Vertex project, location, and vision model are required.")
        self.project = project.strip()
        self.location = location.strip()
        self.model = model.strip()
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._access_token = access_token or _default_access_token

    @property
    def endpoint(self) -> str:
        host = (
            "aiplatform.googleapis.com"
            if self.location == "global"
            else f"{quote(self.location, safe='')}-aiplatform.googleapis.com"
        )
        resource = (
            f"projects/{quote(self.project, safe='')}/locations/"
            f"{quote(self.location, safe='')}/publishers/google/models/"
            f"{quote(self.model, safe='')}"
        )
        return f"https://{host}/v1/{resource}:generateContent"

    def analyze_garment(self, image: bytes) -> GarmentAnalysis:
        if not image:
            raise VisionUnavailableError
        mime_type = _image_mime_type(image)
        request_body = {
            "contents": [
                {
                    "role": "USER",
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": base64.b64encode(image).decode("ascii"),
                            }
                        },
                        {
                            "text": (
                                "Identify the primary garment or accessory. Use only visible "
                                "evidence. Use unknown when material or a detail is uncertain."
                            )
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 512,
                "responseMimeType": "application/json",
                "responseSchema": _RESPONSE_SCHEMA,
            },
            "labels": {"feature": "garment-enrichment"},
        }
        try:
            response = self._client.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self._access_token()}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=request_body,
            )
            response.raise_for_status()
            envelope = response.json()
            text = envelope["candidates"][0]["content"]["parts"][0]["text"]
            payload = _GarmentPayload.model_validate(json.loads(text))
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            raise VisionUnavailableError from exc

        usage = envelope.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount")
        output_tokens = usage.get("candidatesTokenCount")
        return GarmentAnalysis(
            category=payload.category,
            color=payload.color,
            pattern=payload.pattern,
            material=payload.material,
            silhouette=payload.silhouette,
            occasion_tags=payload.occasion_tags,
            category_confidence=payload.category_confidence,
            color_confidence=payload.color_confidence,
            provider="google-vertex",
            model=self.model,
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
        )
