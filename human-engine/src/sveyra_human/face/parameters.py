"""The face, as numbers.

Same idea as `BodyParameters`: a face is a few dozen named measurements, not a
network's latent vector. Fractions are of face length (chin to hairline) unless
a field says otherwise, so a face scales with the head it sits on.

Geometry carries proportion; identity comes mostly from texture. This model is
deliberately coarse because a fitted mesh cannot capture a person's likeness on
its own, and pretending otherwise would push effort into the wrong place.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

# Proportions of a neutral adult face as fractions of face length. Classical
# artistic canon rather than a dataset, so nothing here carries a licence.
_NEUTRAL = {
    "face_width": 0.72,
    "forehead_width": 0.62,
    "forehead_height": 0.31,
    "cheekbone_width": 0.70,
    "cheekbone_height": 0.55,
    "jaw_width": 0.54,
    "jaw_height": 0.30,
    "chin_width": 0.22,
    "chin_projection": 0.07,
    "nose_length": 0.28,
    "nose_width": 0.18,
    "nose_projection": 0.12,
    "eye_spacing": 0.30,
    "eye_width": 0.20,
    "eye_height_position": 0.52,
    "mouth_width": 0.30,
    "mouth_height_position": 0.26,
    "brow_height_position": 0.62,
}

# Anything outside this multiple of neutral is not a face, it is a fitting
# failure. Used to bound the solver.
PLAUSIBLE_SCALE = (0.55, 1.8)


@dataclass
class FaceParameters:
    """Named face dimensions in centimetres.

    `face_length` is chin to hairline. Unset fields are filled from neutral
    proportions scaled by it, so a caller may supply as little as they have.
    """

    face_length: float

    face_width: float | None = None
    forehead_width: float | None = None
    forehead_height: float | None = None
    cheekbone_width: float | None = None
    cheekbone_height: float | None = None
    jaw_width: float | None = None
    jaw_height: float | None = None
    chin_width: float | None = None
    chin_projection: float | None = None
    nose_length: float | None = None
    nose_width: float | None = None
    nose_projection: float | None = None
    eye_spacing: float | None = None
    eye_width: float | None = None
    eye_height_position: float | None = None
    mouth_width: float | None = None
    mouth_height_position: float | None = None
    brow_height_position: float | None = None

    extra: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.face_length <= 0:
            raise ValueError("face_length must be positive")
        if not 8.0 <= self.face_length <= 35.0:
            raise ValueError(f"face_length {self.face_length} cm is not a human face")
        for name, fraction in _NEUTRAL.items():
            if getattr(self, name, None) is None:
                setattr(self, name, round(self.face_length * fraction, 4))

    @classmethod
    def for_head(cls, head_height_cm: float) -> FaceParameters:
        """A neutral face sized to a head.

        The face occupies roughly the lower three quarters of the skull; the
        rest is cranium above the hairline.
        """
        return cls(face_length=round(head_height_cm * 0.74, 4))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> FaceParameters:
        known = {f.name for f in fields(cls)}
        supplied = {k: v for k, v in data.items() if k in known}
        leftover = {
            k: float(v)
            for k, v in data.items()
            if k not in known and isinstance(v, (int, float))
        }
        params = cls(**supplied)  # type: ignore[arg-type]
        params.extra.update(leftover)
        return params

    def solved_fields(self) -> tuple[str, ...]:
        """Fields a landmark fit can actually determine.

        Projections are excluded: a single front view says nothing about depth.
        """
        return (
            "face_width",
            "forehead_width",
            "cheekbone_width",
            "jaw_width",
            "chin_width",
            "nose_length",
            "nose_width",
            "eye_spacing",
            "eye_width",
            "mouth_width",
        )


def neutral_fractions() -> dict[str, float]:
    return dict(_NEUTRAL)
