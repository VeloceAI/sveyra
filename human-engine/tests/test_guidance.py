"""Capture guidance: telling someone what to change, not what is wrong."""

import numpy as np

from sveyra_human.capture.guidance import (
    Severity,
    guide_capture,
    overall_guidance,
)


def frame(height=400, width=250, top=30, bottom=380, left=95, right=155, value=140):
    image = np.full((height, width, 3), value, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=bool)
    mask[top:bottom, left:right] = True
    return image, mask


def codes(guidance):
    return {i.code for i in guidance.instructions}


def test_a_well_framed_shot_needs_no_instruction() -> None:
    image, mask = frame()
    result = guide_capture("front", image, mask, confidence=0.9)
    assert result.usable
    assert result.instructions == []
    assert result.headline == "Looks good."
    assert result.framing_score > 0.9


def test_an_empty_frame_asks_the_person_to_stand_in_it() -> None:
    image, _ = frame()
    result = guide_capture("front", image, np.zeros((400, 250), bool), confidence=0.0)
    assert not result.usable
    assert "no_subject" in codes(result)


def test_a_cropped_subject_blocks_and_says_what_to_do() -> None:
    image, mask = frame(top=200, bottom=340)
    result = guide_capture("front", image, mask, confidence=0.9)
    assert not result.usable
    assert "too_far_or_cropped" in codes(result)
    assert "further away" in result.headline


def test_touching_the_edge_blocks() -> None:
    image, mask = frame(top=0, bottom=399)
    result = guide_capture("front", image, mask, confidence=0.9)
    assert not result.usable
    assert "touching_edge" in codes(result)


def test_being_off_centre_names_the_direction() -> None:
    image, mask = frame(left=15, right=75)
    result = guide_capture("front", image, mask, confidence=0.9)
    assert "off_centre" in codes(result)
    assert "right" in [i.message for i in result.instructions if i.code == "off_centre"][0]


def test_a_dark_photo_advises_more_light() -> None:
    image, mask = frame(value=20)
    assert "too_dark" in codes(guide_capture("front", image, mask, confidence=0.9))


def test_a_blown_out_photo_advises_moving_from_the_light() -> None:
    image, mask = frame(value=252)
    assert "too_bright" in codes(guide_capture("front", image, mask, confidence=0.9))


def test_poor_separation_suggests_a_plainer_wall() -> None:
    image, mask = frame()
    assert "poor_separation" in codes(guide_capture("front", image, mask, confidence=0.1))


def test_blocking_instructions_come_first() -> None:
    """Someone told five things at once fixes none."""
    image, mask = frame(top=200, bottom=340, left=15, right=75, value=20)
    result = guide_capture("front", image, mask, confidence=0.1)
    assert result.instructions[0].severity is Severity.BLOCKING


def test_advisories_do_not_make_a_photo_unusable() -> None:
    image, mask = frame(value=20)
    result = guide_capture("front", image, mask, confidence=0.9)
    assert result.usable
    assert result.instructions


def test_guidance_serialises_for_an_api() -> None:
    image, mask = frame()
    payload = guide_capture("front", image, mask, confidence=0.9).to_dict()
    assert payload["view"] == "front"
    assert payload["usable"] is True
    assert isinstance(payload["instructions"], list)


def test_a_missing_front_view_is_called_out() -> None:
    image, mask = frame()
    views = {"side": guide_capture("side", image, mask, confidence=0.9)}
    assert any("front photo is required" in m for m in overall_guidance(views))


def test_a_missing_side_view_is_advised_not_demanded() -> None:
    image, mask = frame()
    views = {"front": guide_capture("front", image, mask, confidence=0.9)}
    messages = overall_guidance(views)
    assert any("side photo" in m for m in messages)
    assert not any("required" in m for m in messages)
