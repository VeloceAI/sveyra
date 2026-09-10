from importlib.util import find_spec
from uuid import UUID

from sqlalchemy.orm import Session

from app.avatar.port import AvatarPort
from app.repositories.platform_repository import PlatformRepository
from app.schemas.platform_schema import (
    CapabilityReadiness,
    NextAction,
    PersonalModelReadiness,
    PlatformReadinessResponse,
)
from app.stylist.port import StylistPort
from app.vision.port import VisionPort


class PlatformService:
    def __init__(self, repository: PlatformRepository | None = None) -> None:
        self.repository = repository or PlatformRepository()

    def readiness(
        self,
        session: Session,
        user_id: UUID,
        avatar: AvatarPort,
        vision: VisionPort,
        stylist: StylistPort,
    ) -> PlatformReadinessResponse:
        snapshot = self.repository.snapshot(session, user_id)
        core_gates = (
            snapshot.style_ready,
            snapshot.wardrobe_items > 0,
            snapshot.body_ready,
        )
        complete = round(100 * sum(core_gates) / len(core_gates))

        personal = PersonalModelReadiness(
            **snapshot.__dict__,
            core_completion_percent=complete,
            next_action=_next_action(snapshot),
        )
        return PlatformReadinessResponse(
            parity_phase="P0 — coherent product shell",
            product_message=(
                "Build a useful closet and daily styling habit first; add deeper "
                "identity, size, beauty, and 3D fit after the core loop works."
            ),
            personal_model=personal,
            capabilities=_capabilities(avatar, vision, stylist),
        )


def _next_action(snapshot) -> NextAction:
    if not snapshot.style_ready:
        return NextAction(
            label="Set your style direction",
            href="/profile",
            reason="A few preferences keep recommendations personal rather than generic.",
        )
    if snapshot.wardrobe_items == 0:
        return NextAction(
            label="Add your first garment",
            href="/wardrobe/new",
            reason="Owned clothes are the raw material for daily outfits.",
        )
    if not snapshot.body_ready:
        return NextAction(
            label="Create your body foundation",
            href="/avatar",
            reason="Height and body evidence prepare the avatar and later size guidance.",
        )
    if not snapshot.appearance_ready:
        return NextAction(
            label="Tune your color profile",
            href="/appearance",
            reason="Optional color evidence improves outfit and makeup guidance.",
        )
    if snapshot.enriched_items < snapshot.wardrobe_items:
        return NextAction(
            label="Review garment details",
            href="/wardrobe",
            reason="Confirmed garment data makes styling and search more reliable.",
        )
    return NextAction(
        label="Create today's look",
        href="/recommend",
        reason="Your core personal model is ready for an owned-wardrobe recommendation.",
    )


def _capabilities(
    avatar: AvatarPort,
    vision: VisionPort,
    stylist: StylistPort,
) -> list[CapabilityReadiness]:
    avatar_is_local = type(avatar).__name__ == "SveyraEngineAvatar"
    engine_installed = find_spec("sveyra_human") is not None
    vision_is_demo = type(vision).__name__ == "StubVision"
    stylist_is_local = type(stylist).__name__ == "StubStylist"

    avatar_ready = avatar_is_local and engine_installed
    return [
        CapabilityReadiness(
            key="closet",
            label="Digital closet",
            status="ready",
            provider="SVYERA core",
            summary="Store owned garments, media, metadata, and wear history.",
            limitation="Batch import and editorial background cleanup are next.",
            href="/wardrobe",
        ),
        CapabilityReadiness(
            key="garment_vision",
            label="Garment identification",
            status="demo" if vision_is_demo else "ready",
            provider="Local deterministic demo" if vision_is_demo else type(vision).__name__,
            summary="Extract structured garment cues through a provider-neutral port.",
            limitation=(
                "The configured adapter is a test stub, not real image recognition."
                if vision_is_demo
                else None
            ),
            href="/wardrobe",
        ),
        CapabilityReadiness(
            key="stylist",
            label="Outfit ranking",
            status="ready",
            provider=(
                "SVYERA deterministic ranker" if stylist_is_local else type(stylist).__name__
            ),
            summary="Rank owned-wardrobe combinations using profile and garment evidence.",
            limitation="Weather, item locking, slot swapping, and feedback learning are next.",
            href="/recommend",
        ),
        CapabilityReadiness(
            key="avatar",
            label="3D human foundation",
            status="ready" if avatar_ready else "setup_required",
            provider=("SVYERA Human Engine" if avatar_is_local else type(avatar).__name__),
            summary="Generate a measurable, rigged canonical GLB locally.",
            limitation=(
                "Identity, photoreal materials, hair, and dressed garments are not "
                "fitted yet."
            ),
            href="/human-engine",
        ),
        CapabilityReadiness(
            key="visual_try_on",
            label="Photoreal visual try-on",
            status="setup_required",
            provider="No provider configured",
            summary="Render an outfit on a recognizable person or avatar image.",
            limitation="A TryOnPort adapter and provider credentials still need implementation.",
            href="/avatar",
        ),
        CapabilityReadiness(
            key="metric_fit",
            label="Metric size and cloth fit",
            status="planned",
            provider="SVYERA fit pipeline",
            summary="Combine body, garment measurements, brand charts, and later cloth physics.",
            limitation="Generated try-on imagery will never be presented as physical fit proof.",
        ),
    ]
