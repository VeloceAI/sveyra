from dataclasses import dataclass, field
from uuid import UUID

# Deterministic wardrobe ranking. Future AI adapters implement StylistPort
# without changing the HTTP recommendation contract.

TOP_CATEGORIES = frozenset(
    {
        "shirt",
        "top",
        "blouse",
        "sweater",
        "t-shirt",
        "tee",
        "jacket",
        "hoodie",
        "coat",
    }
)
BOTTOM_CATEGORIES = frozenset(
    {
        "trousers",
        "pants",
        "jeans",
        "skirt",
        "shorts",
        "chinos",
    }
)
SHOE_CATEGORIES = frozenset(
    {
        "shoes",
        "sneakers",
        "boots",
        "sandals",
        "loafers",
    }
)
NEUTRAL_COLORS = frozenset(
    {
        "black",
        "white",
        "gray",
        "grey",
        "navy",
        "beige",
        "cream",
        "khaki",
        "brown",
        "tan",
    }
)

MAX_CANDIDATES = 5


@dataclass(frozen=True)
class WardrobeItemSignal:
    id: UUID
    category: str
    color: str
    brand: str
    attributes: dict[str, object]


@dataclass(frozen=True)
class RankedOutfit:
    item_ids: list[UUID]
    score: float
    rationale: str


@dataclass(frozen=True)
class RankingContext:
    occasion: str
    items: list[WardrobeItemSignal]
    preferences: dict[str, object] = field(default_factory=dict)
    dislikes: dict[str, object] = field(default_factory=dict)
    budget: dict[str, object] = field(default_factory=dict)
    fit_preferences: dict[str, object] = field(default_factory=dict)


def _normalize(value: str) -> str:
    return value.strip().lower()


def _bucket(category: str) -> str | None:
    key = _normalize(category)
    if key in TOP_CATEGORIES:
        return "top"
    if key in BOTTOM_CATEGORIES:
        return "bottom"
    if key in SHOE_CATEGORIES:
        return "shoes"
    return None


def _color_compatible(first: str, second: str) -> bool:
    a = _normalize(first)
    b = _normalize(second)
    if not a or not b:
        return True
    if a == b:
        return True
    if a in NEUTRAL_COLORS or b in NEUTRAL_COLORS:
        return True
    return False


def _cv(attrs: dict[str, object]) -> dict[str, object]:
    raw = attrs.get("cv")
    return dict(raw) if isinstance(raw, dict) else {}


def _string_needles(mapping: dict[str, object] | None) -> list[str]:
    if not mapping:
        return []
    needles: list[str] = []
    for value in mapping.values():
        if isinstance(value, str) and value.strip():
            needles.append(_normalize(value))
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, str) and entry.strip():
                    needles.append(_normalize(entry))
    return needles


def _item_text_blobs(item: WardrobeItemSignal) -> list[str]:
    blobs = [
        _normalize(item.category),
        _normalize(item.color),
        _normalize(item.brand),
    ]
    attrs = item.attributes or {}
    for key in ("occasion", "occasions", "style", "pattern", "material", "fit", "silhouette"):
        raw = attrs.get(key)
        if isinstance(raw, str) and raw.strip():
            blobs.append(_normalize(raw))
        elif isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, str) and entry.strip():
                    blobs.append(_normalize(entry))
    cv = _cv(attrs)
    for key in ("pattern", "material", "silhouette"):
        raw = cv.get(key)
        if isinstance(raw, str) and raw.strip():
            blobs.append(_normalize(raw))
    tags = cv.get("occasion_tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.strip():
                blobs.append(_normalize(tag))
    return blobs


def _text_contains_any(blobs: list[str], needles: list[str]) -> bool:
    return any(needle and any(needle in blob for blob in blobs) for needle in needles)


def _occasion_bonus(item: WardrobeItemSignal, occasion: str) -> tuple[float, str | None]:
    target = _normalize(occasion)
    if not target:
        return 0.0, None
    attrs = item.attributes or {}
    for key in ("occasion", "occasions", "style"):
        raw = attrs.get(key)
        if isinstance(raw, str) and target in _normalize(raw):
            return 2.0, f"matches {target} from item attributes"
        if isinstance(raw, list) and any(
            isinstance(entry, str) and target in _normalize(entry) for entry in raw
        ):
            return 2.0, f"matches {target} from item attributes"
    cv = _cv(attrs)
    tags = cv.get("occasion_tags")
    if isinstance(tags, list) and any(
        isinstance(tag, str) and target in _normalize(tag) for tag in tags
    ):
        return 3.0, f"CV occasion tags support {target}"
    if target in _normalize(item.category):
        return 1.0, f"category aligns with {target}"
    return 0.0, None


def _style_bonus(item: WardrobeItemSignal, preferences: dict[str, object]) -> tuple[float, str | None]:
    needles = _string_needles(preferences)
    if not needles:
        return 0.0, None
    blobs = _item_text_blobs(item)
    style = preferences.get("style")
    if isinstance(style, str) and style.strip():
        needle = _normalize(style)
        if _text_contains_any(blobs, [needle]):
            return 2.0, f"fits your {needle} style preference"
    if _text_contains_any(blobs, needles):
        return 1.0, "aligns with your style preferences"
    return 0.0, None


def _dislike_penalty(item: WardrobeItemSignal, dislikes: dict[str, object]) -> tuple[float, str | None]:
    needles = _string_needles(dislikes)
    if not needles:
        return 0.0, None
    blobs = _item_text_blobs(item)
    hits = [needle for needle in needles if _text_contains_any(blobs, [needle])]
    if not hits:
        return 0.0, None
    return float(3.0 * len(hits)), f"includes disliked cue ({hits[0]})"


def _budget_bonus(item: WardrobeItemSignal, budget: dict[str, object]) -> tuple[float, str | None]:
    if not budget:
        return 0.0, None
    max_price = budget.get("max")
    price = (item.attributes or {}).get("price")
    if isinstance(max_price, (int, float)) and isinstance(price, (int, float)):
        if float(price) <= float(max_price):
            return 1.0, "stays within your budget"
        return -2.0, "exceeds your budget max"
    brands = budget.get("brands") or budget.get("preferred_brands")
    if isinstance(brands, list):
        brand_needles = [_normalize(b) for b in brands if isinstance(b, str) and b.strip()]
        if _normalize(item.brand) in brand_needles:
            return 1.0, "matches a preferred budget brand"
    return 0.0, None


def _fit_bonus(
    item: WardrobeItemSignal, fit_preferences: dict[str, object]
) -> tuple[float, str | None]:
    needles = _string_needles(fit_preferences)
    if not needles:
        return 0.0, None
    blobs = _item_text_blobs(item)
    ease = fit_preferences.get("ease") or fit_preferences.get("fit")
    if isinstance(ease, str) and ease.strip():
        needle = _normalize(ease)
        if _text_contains_any(blobs, [needle]):
            return 1.5, f"supports your {needle} fit preference"
    if _text_contains_any(blobs, needles):
        return 1.0, "supports your fit preferences"
    return 0.0, None


def _cv_detail_bonus(item: WardrobeItemSignal) -> tuple[float, str | None]:
    cv = _cv(item.attributes or {})
    details: list[str] = []
    for key in ("pattern", "material", "silhouette"):
        value = cv.get(key)
        if isinstance(value, str) and value.strip():
            details.append(f"{key} {_normalize(value)}")
    if not details:
        return 0.0, None
    return 0.5, f"uses CV cues ({', '.join(details[:2])})"


def _score_combo(
    items: list[WardrobeItemSignal],
    occasion: str,
    preferences: dict[str, object],
    dislikes: dict[str, object],
    budget: dict[str, object],
    fit_preferences: dict[str, object],
) -> tuple[float, str]:
    score = float(len(items)) * 3.0
    reasons: list[str] = []

    colors = [item.color for item in items if item.color]
    if len(colors) >= 2:
        compatible = all(
            _color_compatible(colors[index], colors[index + 1])
            for index in range(len(colors) - 1)
        )
        if compatible:
            score += 2.0
            reasons.append("coordinated colors")
        else:
            score -= 1.0

    for item in items:
        for bonus, note in (
            _occasion_bonus(item, occasion),
            _style_bonus(item, preferences),
            _budget_bonus(item, budget),
            _fit_bonus(item, fit_preferences),
            _cv_detail_bonus(item),
        ):
            score += bonus
            if note and note not in reasons:
                reasons.append(note)
        penalty, dislike_note = _dislike_penalty(item, dislikes)
        score -= penalty
        if dislike_note and dislike_note not in reasons:
            reasons.append(dislike_note)

    buckets = {_bucket(item.category) for item in items}
    if "top" in buckets and "bottom" in buckets:
        score += 4.0
        reasons.append("balanced top and bottom")
    if "shoes" in buckets:
        score += 1.5
        reasons.append("includes shoes")

    if not dislikes or not any("disliked cue" in reason for reason in reasons):
        if dislikes:
            reasons.append("avoids your stated dislikes")

    categories = ", ".join(item.category for item in items)
    occasion_label = _normalize(occasion) or "selected"
    if reasons:
        detail = "; ".join(reasons[:4])
        rationale = (
            f"For {occasion_label}, this {categories} look works because {detail}."
        )
    else:
        rationale = (
            f"A practical {occasion_label} combination using your "
            f"available wardrobe ({categories})."
        )
    return score, rationale


def rank_outfits(
    items: list[WardrobeItemSignal],
    occasion: str,
    *,
    preferences: dict[str, object] | None = None,
    dislikes: dict[str, object] | None = None,
    budget: dict[str, object] | None = None,
    fit_preferences: dict[str, object] | None = None,
    limit: int = MAX_CANDIDATES,
) -> list[RankedOutfit]:
    context = RankingContext(
        occasion=occasion,
        items=items,
        preferences=dict(preferences or {}),
        dislikes=dict(dislikes or {}),
        budget=dict(budget or {}),
        fit_preferences=dict(fit_preferences or {}),
    )
    return rank_outfits_from_context(context, limit=limit)


def rank_outfits_from_context(
    context: RankingContext, *, limit: int = MAX_CANDIDATES
) -> list[RankedOutfit]:
    items = context.items
    if not items:
        return []

    tops = [item for item in items if _bucket(item.category) == "top"]
    bottoms = [item for item in items if _bucket(item.category) == "bottom"]
    shoes = [item for item in items if _bucket(item.category) == "shoes"]
    other = [item for item in items if _bucket(item.category) is None]

    candidates: list[RankedOutfit] = []
    used_signatures: set[tuple[UUID, ...]] = set()

    def consider(combo: list[WardrobeItemSignal]) -> None:
        if not combo:
            return
        signature = tuple(sorted(item.id for item in combo))
        if signature in used_signatures:
            return
        used_signatures.add(signature)
        score, rationale = _score_combo(
            combo,
            context.occasion,
            context.preferences,
            context.dislikes,
            context.budget,
            context.fit_preferences,
        )
        candidates.append(
            RankedOutfit(
                item_ids=[item.id for item in combo],
                score=score,
                rationale=rationale,
            )
        )

    if tops and bottoms:
        for top in tops:
            for bottom in bottoms:
                consider([top, bottom])
                for shoe in shoes[:3]:
                    consider([top, bottom, shoe])
    elif tops and other:
        for top in tops:
            for extra in other[:5]:
                consider([top, extra])
    elif bottoms and other:
        for bottom in bottoms:
            for extra in other[:5]:
                consider([bottom, extra])
    elif len(items) >= 2:
        for index, first in enumerate(items):
            for second in items[index + 1 :]:
                consider([first, second])
                if len(candidates) >= limit * 3:
                    break
            if len(candidates) >= limit * 3:
                break
    elif len(items) == 1:
        return []

    candidates.sort(key=lambda entry: (-entry.score, [str(item_id) for item_id in entry.item_ids]))
    return candidates[:limit]
