import pytest

from app.services.category_taxonomy import (
    ACCESSORY,
    BOTTOM,
    ONEPIECE,
    OUTERWEAR,
    SHOES,
    TOP,
    bucket_for,
    covers_top_and_bottom,
)


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("shirt", TOP),
        ("polo", TOP),
        ("t-shirt", TOP),
        ("tshirt", TOP),
        ("vest", TOP),
        ("jeans", BOTTOM),
        ("leggings", BOTTOM),
        ("skirt", BOTTOM),
        ("shoes", SHOES),
        ("heels", SHOES),
        ("flats", SHOES),
        ("trainers", SHOES),
        ("dress", ONEPIECE),
        ("jumpsuit", ONEPIECE),
        ("romper", ONEPIECE),
        ("blazer", OUTERWEAR),
        ("cardigan", OUTERWEAR),
        ("jacket", OUTERWEAR),
        ("scarf", ACCESSORY),
    ],
)
def test_known_categories_bucket_correctly(category: str, expected: str) -> None:
    assert bucket_for(category) == expected


@pytest.mark.parametrize("category", ["sneaker", "sneakers", "boot", "boots", "loafer"])
def test_singular_and_plural_both_resolve(category: str) -> None:
    assert bucket_for(category) == SHOES


def test_dress_is_not_truncated_by_plural_handling() -> None:
    # "dress" ends in "s"; an exact match must win over stripping it to "dres".
    assert bucket_for("dress") == ONEPIECE


@pytest.mark.parametrize("category", ["  Shirt  ", "T_SHIRT", "Crop-Top", "TANK TOP"])
def test_casing_spacing_and_separators_are_normalized(category: str) -> None:
    assert bucket_for(category) == TOP


@pytest.mark.parametrize("category", ["", "   ", "kimono", "unclassifiable thing"])
def test_unknown_categories_return_none(category: str) -> None:
    assert bucket_for(category) is None


def test_outerwear_is_not_treated_as_a_top() -> None:
    # A jacket must never stand in for the shirt underneath it.
    assert bucket_for("jacket") != TOP
    assert not covers_top_and_bottom({OUTERWEAR, BOTTOM})


def test_a_onepiece_covers_both_halves() -> None:
    assert covers_top_and_bottom({ONEPIECE})
    assert covers_top_and_bottom({TOP, BOTTOM})
    assert not covers_top_and_bottom({TOP})
    assert not covers_top_and_bottom({BOTTOM, SHOES})
