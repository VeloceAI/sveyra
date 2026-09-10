from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppearanceProfileNotFoundError
from app.models.appearance_profile import AppearanceProfile
from app.repositories.appearance_repository import AppearanceRepository
from app.schemas.appearance_schema import (
    AppearanceProfilePersistRequest,
    AppearanceProfileResponse,
    ColourCombination,
    ColourSwatch,
    ContrastLevel,
    MakeupGuidance,
    PersonalPalette,
    SkinDepth,
    Undertone,
)

PALETTES: dict[Undertone, dict[str, object]] = {
    Undertone.WARM: {
        "best": [
            ("Paprika", "#B84A32"),
            ("Marigold", "#D99A24"),
            ("Olive", "#65733B"),
            ("Warm teal", "#177C78"),
            ("Coral", "#E56B5D"),
            ("Aubergine", "#643A57"),
        ],
        "neutrals": [
            ("Ivory", "#F3E8D3"),
            ("Camel", "#B78555"),
            ("Chocolate", "#56382D"),
            ("Warm navy", "#293B4A"),
        ],
        "metals": ["yellow gold", "bronze", "copper"],
        "eyes": "Bronze, olive, warm brown, and deep plum.",
    },
    Undertone.COOL: {
        "best": [
            ("Sapphire", "#2657A7"),
            ("Berry", "#A53F68"),
            ("Blue red", "#BC3148"),
            ("Pine", "#1F6B59"),
            ("Lavender", "#8D78B8"),
            ("Icy blue", "#9CCDE0"),
        ],
        "neutrals": [
            ("Soft white", "#F2F3F5"),
            ("Charcoal", "#3E4248"),
            ("Cool taupe", "#887D79"),
            ("Ink navy", "#202F4A"),
        ],
        "metals": ["silver", "white gold", "platinum"],
        "eyes": "Taupe, pewter, cool cocoa, plum, and navy.",
    },
    Undertone.NEUTRAL: {
        "best": [
            ("Jade", "#2E806C"),
            ("Dusty rose", "#B96879"),
            ("Soft cobalt", "#3868A6"),
            ("Mulberry", "#753D59"),
            ("Muted coral", "#C96C62"),
            ("Periwinkle", "#7A82BF"),
        ],
        "neutrals": [
            ("Oyster", "#E9E2D6"),
            ("Mushroom", "#8D8175"),
            ("Espresso", "#493832"),
            ("Balanced navy", "#26384D"),
        ],
        "metals": ["mixed metals", "champagne gold", "soft silver"],
        "eyes": "Rose brown, taupe, balanced bronze, jade, and soft charcoal.",
    },
    Undertone.OLIVE: {
        "best": [
            ("Deep teal", "#176A67"),
            ("Brick", "#A84B3C"),
            ("Petrol blue", "#245D73"),
            ("Burgundy", "#6F2F45"),
            ("Saffron", "#C58B20"),
            ("Forest", "#315C3B"),
        ],
        "neutrals": [
            ("Cream", "#EEE2C7"),
            ("Khaki", "#8B8062"),
            ("Deep brown", "#49352B"),
            ("Green navy", "#243E43"),
        ],
        "metals": ["antique gold", "bronze", "oxidised silver"],
        "eyes": "Antique gold, khaki, espresso, petrol, and burgundy.",
    },
}


LIPS = {
    SkinDepth.VERY_LIGHT: "rose pink, soft coral, or a sheer berry",
    SkinDepth.LIGHT: "peach rose, pink nude, or raspberry",
    SkinDepth.MEDIUM: "caramel nude, warm rose, or cranberry",
    SkinDepth.TAN: "terracotta, spiced rose, or deep coral",
    SkinDepth.DEEP: "brick, rich berry, cocoa rose, or wine",
    SkinDepth.VERY_DEEP: "oxblood, black cherry, deep plum, or rich mahogany",
}


CHEEKS = {
    Undertone.WARM: "apricot, warm peach, or terracotta",
    Undertone.COOL: "cool rose, mauve, or berry",
    Undertone.NEUTRAL: "balanced rose, soft coral, or muted berry",
    Undertone.OLIVE: "burnished peach, brick rose, or warm berry",
}


def _swatches(values: object) -> list[ColourSwatch]:
    assert isinstance(values, list)
    return [ColourSwatch(name=name, hex=hex_value) for name, hex_value in values]


def build_personal_palette(payload: AppearanceProfilePersistRequest) -> PersonalPalette:
    spec = PALETTES[payload.skin.undertone]
    best = _swatches(spec["best"])
    neutrals = _swatches(spec["neutrals"])
    contrast = payload.colour_analysis.contrast
    if contrast is ContrastLevel.LOW:
        contrast_guidance = "Use tonal combinations with small light-to-dark steps."
    elif contrast is ContrastLevel.HIGH:
        contrast_guidance = "Use clear light-dark contrast and decisive accent colours."
    else:
        contrast_guidance = "Use one defined accent with balanced mid-value neutrals."

    combinations = [
        ColourCombination(
            name="Everyday tonal",
            colours=[neutrals[0], neutrals[1], best[0]],
            guidance=contrast_guidance,
        ),
        ColourCombination(
            name="Polished contrast",
            colours=[neutrals[0], neutrals[3], best[1]],
            guidance="Let the accent occupy the smallest area for an intentional finish.",
        ),
        ColourCombination(
            name="Colour-led",
            colours=[best[2], best[3], neutrals[2]],
            guidance="Repeat one colour in a small accessory or makeup detail.",
        ),
    ]
    intensity = payload.makeup.intensity.value.replace("_", " ")
    return PersonalPalette(
        title=(
            f"{payload.skin.undertone.value.title()} "
            f"{payload.skin.depth.value.replace('_', ' ')} palette"
        ),
        summary=(
            f"A {contrast.value}-contrast starter palette based on confirmed appearance inputs. "
            "Review it in daylight and edit any colour that does not feel accurate."
        ),
        best_colours=best,
        neutrals=neutrals,
        metals=list(spec["metals"]),  # type: ignore[arg-type]
        combinations=combinations,
        makeup=MakeupGuidance(
            complexion=(
                f"Match the {payload.skin.undertone.value} undertone at jaw and neck; "
                "do not use foundation to change skin depth."
            ),
            cheeks=str(CHEEKS[payload.skin.undertone]),
            lips=LIPS[payload.skin.depth],
            eyes=str(spec["eyes"]),
            finish=f"{payload.makeup.finish.value} finish at {intensity} intensity.",
        ),
    )


class AppearanceService:
    def __init__(self, repository: AppearanceRepository | None = None) -> None:
        self.repository = repository or AppearanceRepository()

    def upsert(
        self,
        session: Session,
        user_id: UUID,
        payload: AppearanceProfilePersistRequest,
    ) -> AppearanceProfileResponse:
        values = self._stored_values(payload)
        profile = self.repository.get_by_user_id(session, user_id)
        if profile is None:
            profile = self.repository.create(session, user_id, values)
        else:
            profile = self.repository.update(profile, values)
        session.commit()
        session.refresh(profile)
        return self._to_response(profile)

    def get(self, session: Session, user_id: UUID) -> AppearanceProfileResponse:
        profile = self.repository.get_by_user_id(session, user_id)
        if profile is None:
            raise AppearanceProfileNotFoundError
        return self._to_response(profile)

    def _stored_values(
        self,
        payload: AppearanceProfilePersistRequest,
    ) -> dict[str, dict[str, object]]:
        return {
            "skin": payload.skin.model_dump(mode="json"),
            "face": payload.face.model_dump(mode="json"),
            "eyes": payload.eyes.model_dump(mode="json"),
            "hair": payload.hair.model_dump(mode="json"),
            "colour_analysis": payload.colour_analysis.model_dump(mode="json"),
            "makeup": payload.makeup.model_dump(mode="json"),
            "evidence": payload.evidence.model_dump(mode="json"),
        }

    def _to_response(self, profile: AppearanceProfile) -> AppearanceProfileResponse:
        payload = AppearanceProfilePersistRequest(
            skin=profile.skin,
            face=profile.face,
            eyes=profile.eyes,
            hair=profile.hair,
            colour_analysis=profile.colour_analysis,
            makeup=profile.makeup,
            evidence=profile.evidence,
        )
        return AppearanceProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            **payload.model_dump(),
            palette=build_personal_palette(payload),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
