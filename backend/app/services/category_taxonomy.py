"""Maps free-text garment categories onto the buckets outfit building reasons about.

Categories arrive from users and from vision output, so the vocabulary is open.
Anything unrecognised buckets as None and is still offered as a layering extra
rather than disappearing from the wardrobe.
"""

TOP = "top"
BOTTOM = "bottom"
SHOES = "shoes"
ONEPIECE = "onepiece"
OUTERWEAR = "outerwear"
ACCESSORY = "accessory"

TOP_CATEGORIES = frozenset(
    {
        "blouse",
        "bodysuit",
        "camisole",
        "crop top",
        "henley",
        "hoodie",
        "jersey",
        "knit",
        "long sleeve",
        "polo",
        "pullover",
        "shirt",
        "sweater",
        "sweatshirt",
        "t-shirt",
        "tank",
        "tank top",
        "tee",
        "top",
        "tshirt",
        "turtleneck",
        "vest",
    }
)

BOTTOM_CATEGORIES = frozenset(
    {
        "bottom",
        "cargos",
        "chinos",
        "corduroys",
        "culottes",
        "denim",
        "joggers",
        "jeans",
        "leggings",
        "pants",
        "shorts",
        "skirt",
        "slacks",
        "sweatpants",
        "trousers",
    }
)

SHOE_CATEGORIES = frozenset(
    {
        "boots",
        "brogues",
        "clogs",
        "derbies",
        "espadrilles",
        "flats",
        "footwear",
        "heels",
        "loafers",
        "mules",
        "oxfords",
        "pumps",
        "sandals",
        "shoes",
        "slides",
        "sneakers",
        "trainers",
    }
)

# One-piece garments cover the top and bottom halves on their own, so an outfit
# built from one is already complete without a separate top or bottom.
ONEPIECE_CATEGORIES = frozenset(
    {
        "dress",
        "gown",
        "jumpsuit",
        "onesie",
        "overalls",
        "playsuit",
        "romper",
        "sundress",
    }
)

# Layers worn over a top. Kept apart from TOP so a jacket is never mistaken for
# the shirt underneath it.
OUTERWEAR_CATEGORIES = frozenset(
    {
        "anorak",
        "blazer",
        "bomber",
        "cardigan",
        "coat",
        "jacket",
        "overcoat",
        "parka",
        "raincoat",
        "trench",
        "windbreaker",
    }
)

ACCESSORY_CATEGORIES = frozenset(
    {
        "bag",
        "belt",
        "cap",
        "gloves",
        "handbag",
        "hat",
        "jewelry",
        "necklace",
        "scarf",
        "sunglasses",
        "tie",
        "watch",
    }
)

_BUCKETS: tuple[tuple[frozenset[str], str], ...] = (
    (TOP_CATEGORIES, TOP),
    (BOTTOM_CATEGORIES, BOTTOM),
    (SHOE_CATEGORIES, SHOES),
    (ONEPIECE_CATEGORIES, ONEPIECE),
    (OUTERWEAR_CATEGORIES, OUTERWEAR),
    (ACCESSORY_CATEGORIES, ACCESSORY),
)

def normalize(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


# Keys go through normalize too, so "t-shirt" in the set above still matches the
# normalized "t shirt" a caller sends.
_LOOKUP: dict[str, str] = {
    normalize(category): bucket for categories, bucket in _BUCKETS for category in categories
}


def bucket_for(category: str) -> str | None:
    """Return the bucket for a category, or None when it is not recognised."""
    key = normalize(category)
    if not key:
        return None
    direct = _LOOKUP.get(key)
    if direct is not None:
        return direct
    # Users write "sneaker" as often as "sneakers"; try the other number before
    # giving up. Exact matches above always win, so "dress" is never truncated.
    if key.endswith("s"):
        return _LOOKUP.get(key[:-1])
    return _LOOKUP.get(f"{key}s")


def covers_top_and_bottom(buckets: set[str | None]) -> bool:
    return ONEPIECE in buckets or (TOP in buckets and BOTTOM in buckets)
