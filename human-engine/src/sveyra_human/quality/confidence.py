"""Confidence reporting.

The engine must say when it is guessing. A parametric build has no photographic
evidence at all, and reports that plainly rather than claiming certainty.
"""

from __future__ import annotations

from sveyra_human.api.models import QualityReport


def parametric_report(supplied_measurements: int, total_parameters: int) -> QualityReport:
    """Confidence for a build with no photographs.

    Scaled by how much the caller actually specified: a body derived entirely
    from neutral proportions is a template, not a measurement.
    """
    if total_parameters <= 0:
        raise ValueError("total_parameters must be positive")
    ratio = min(1.0, supplied_measurements / total_parameters)
    warnings = [
        "No photograph informed this body. Dimensions are those supplied or "
        "inferred from neutral proportions."
    ]
    if ratio < 0.25:
        warnings.append(
            "Most dimensions came from neutral proportions rather than from the "
            "caller, so this is close to a generic body at the given height."
        )
    return QualityReport(overall=round(0.3 + 0.5 * ratio, 4), views={}, warnings=warnings)
