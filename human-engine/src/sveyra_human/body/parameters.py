"""The person, as numbers.

A body is described by a few dozen named measurements rather than by thousands
of independent vertices. Everything downstream - cross sections, cage, surface
mesh, skeleton - is a pure function of this object, which is what makes an
avatar reproducible from JSON without the original photographs.

Lengths are centimetres. Fractions are 0-1 of standing height.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

# Proportions of a neutral adult, expressed as fractions of standing height so
# that a body can be generated from height alone. Sources are anthropometric
# rules of thumb, not a dataset, so they carry no licence.
_NEUTRAL = {
    "shoulder_width": 0.245,
    "shoulder_depth": 0.105,
    "shoulder_slope": 0.030,
    "neck_width": 0.070,
    "neck_length": 0.052,
    "chest_width": 0.190,
    "chest_depth": 0.115,
    "waist_width": 0.160,
    "waist_depth": 0.105,
    "hip_width": 0.195,
    "hip_depth": 0.125,
    "upper_arm_length": 0.172,
    "upper_arm_radius": 0.035,
    "forearm_length": 0.157,
    "forearm_radius": 0.027,
    "thigh_length": 0.245,
    "thigh_width": 0.098,
    "thigh_depth": 0.098,
    "calf_length": 0.246,
    "calf_width": 0.068,
    "calf_depth": 0.070,
    "ankle_width": 0.038,
    "head_height": 0.130,
    "head_width": 0.092,
    "head_depth": 0.115,
}

# Fraction of standing height at which each landmark sits, measured from the
# floor. These drive where cross sections are sampled.
_LEVELS = {
    "ankle": 0.039,
    "calf": 0.130,
    "knee": 0.285,
    "thigh": 0.400,
    "hip": 0.520,
    "waist": 0.620,
    "chest": 0.720,
    "shoulder": 0.818,
    "neck": 0.870,
    "head": 1.000,
}


@dataclass
class BodyParameters:
    """Named body dimensions in centimetres.

    Any field left at None is filled from neutral proportions scaled by height,
    so a caller may supply as few or as many measurements as they actually have.
    """

    height: float

    shoulder_width: float | None = None
    shoulder_depth: float | None = None
    shoulder_slope: float | None = None

    neck_width: float | None = None
    neck_length: float | None = None

    chest_width: float | None = None
    chest_depth: float | None = None

    waist_width: float | None = None
    waist_depth: float | None = None
    waist_position: float | None = None

    hip_width: float | None = None
    hip_depth: float | None = None

    upper_arm_length: float | None = None
    upper_arm_radius: float | None = None
    forearm_length: float | None = None
    forearm_radius: float | None = None

    thigh_length: float | None = None
    thigh_width: float | None = None
    thigh_depth: float | None = None
    calf_length: float | None = None
    calf_width: float | None = None
    calf_depth: float | None = None
    ankle_width: float | None = None

    head_height: float | None = None
    head_width: float | None = None
    head_depth: float | None = None

    # Parameters from the wider design list that no solver reads yet. Kept as a
    # bag rather than as fields so adding one later is not a schema break.
    extra: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.height <= 0:
            raise ValueError("height must be positive")
        if not 50.0 <= self.height <= 260.0:
            raise ValueError(f"height {self.height} cm is outside the supported range")
        for name, fraction in _NEUTRAL.items():
            if getattr(self, name, None) is None:
                setattr(self, name, round(self.height * fraction, 3))
        if self.waist_position is None:
            self.waist_position = _LEVELS["waist"]

    def level_cm(self, landmark: str) -> float:
        """Height above the floor, in centimetres, of a named landmark."""
        if landmark == "waist":
            return self.height * float(self.waist_position)
        return self.height * _LEVELS[landmark]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BodyParameters:
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


def landmark_levels() -> dict[str, float]:
    return dict(_LEVELS)
