from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class SkinDepth(StrEnum):
    VERY_LIGHT = "very_light"
    LIGHT = "light"
    MEDIUM = "medium"
    TAN = "tan"
    DEEP = "deep"
    VERY_DEEP = "very_deep"


class Undertone(StrEnum):
    COOL = "cool"
    NEUTRAL = "neutral"
    WARM = "warm"
    OLIVE = "olive"


class ContrastLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FaceShape(StrEnum):
    UNSPECIFIED = "unspecified"
    OVAL = "oval"
    ROUND = "round"
    SQUARE = "square"
    HEART = "heart"
    OBLONG = "oblong"
    DIAMOND = "diamond"


class HairTexture(StrEnum):
    STRAIGHT = "straight"
    WAVY = "wavy"
    CURLY = "curly"
    COILY = "coily"
    PROTECTIVE = "protective"
    SHAVED = "shaved"


class MakeupIntensity(StrEnum):
    NONE = "none"
    NATURAL = "natural"
    POLISHED = "polished"
    STATEMENT = "statement"


class MakeupFinish(StrEnum):
    NATURAL = "natural"
    MATTE = "matte"
    DEWY = "dewy"
    SATIN = "satin"


class EvidenceSource(StrEnum):
    SELF_REPORTED = "self_reported"
    PHOTO_ESTIMATE = "photo_estimate"
    PROFESSIONAL = "professional"


class SkinAppearance(StrictRequestModel):
    tone_hex: str = Field(default="#B98267", pattern=r"^#[0-9A-Fa-f]{6}$")
    depth: SkinDepth = SkinDepth.MEDIUM
    undertone: Undertone = Undertone.NEUTRAL
    sensitive: bool = False


class FaceAppearance(StrictRequestModel):
    shape: FaceShape = FaceShape.UNSPECIFIED


class EyeAppearance(StrictRequestModel):
    color: str = Field(default="brown", min_length=1, max_length=40)


class HairAppearance(StrictRequestModel):
    color: str = Field(default="dark brown", min_length=1, max_length=40)
    texture: HairTexture = HairTexture.WAVY
    chemically_treated: bool = False


class ColourAnalysis(StrictRequestModel):
    contrast: ContrastLevel = ContrastLevel.MEDIUM


class MakeupPreferences(StrictRequestModel):
    intensity: MakeupIntensity = MakeupIntensity.NATURAL
    finish: MakeupFinish = MakeupFinish.NATURAL
    focus: list[str] = Field(default_factory=list, max_length=8)
    avoid: list[str] = Field(default_factory=list, max_length=12)


class AppearanceEvidence(StrictRequestModel):
    source: EvidenceSource = EvidenceSource.SELF_REPORTED
    user_confirmed: bool = True
    confidence: float = Field(default=1.0, ge=0, le=1)


class AppearanceProfilePersistRequest(StrictRequestModel):
    skin: SkinAppearance = Field(default_factory=SkinAppearance)
    face: FaceAppearance = Field(default_factory=FaceAppearance)
    eyes: EyeAppearance = Field(default_factory=EyeAppearance)
    hair: HairAppearance = Field(default_factory=HairAppearance)
    colour_analysis: ColourAnalysis = Field(default_factory=ColourAnalysis)
    makeup: MakeupPreferences = Field(default_factory=MakeupPreferences)
    evidence: AppearanceEvidence = Field(default_factory=AppearanceEvidence)


class ColourSwatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    hex: str


class ColourCombination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    colours: list[ColourSwatch]
    guidance: str


class MakeupGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complexion: str
    cheeks: str
    lips: str
    eyes: str
    finish: str


class PersonalPalette(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    best_colours: list[ColourSwatch]
    neutrals: list[ColourSwatch]
    metals: list[str]
    combinations: list[ColourCombination]
    makeup: MakeupGuidance


class AppearanceProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    skin: SkinAppearance
    face: FaceAppearance
    eyes: EyeAppearance
    hair: HairAppearance
    colour_analysis: ColourAnalysis
    makeup: MakeupPreferences
    evidence: AppearanceEvidence
    palette: PersonalPalette
    created_at: datetime | None
    updated_at: datetime | None
