from typing import Literal

from pydantic import BaseModel, ConfigDict

CapabilityStatus = Literal["ready", "demo", "setup_required", "planned"]


class NextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    href: str
    reason: str


class PersonalModelReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style_ready: bool
    appearance_ready: bool
    body_ready: bool
    body_measurement_count: int
    wardrobe_items: int
    enriched_items: int
    core_completion_percent: int
    next_action: NextAction


class CapabilityReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    status: CapabilityStatus
    provider: str
    summary: str
    limitation: str | None = None
    href: str | None = None


class PlatformReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parity_phase: str
    product_message: str
    personal_model: PersonalModelReadiness
    capabilities: list[CapabilityReadiness]
