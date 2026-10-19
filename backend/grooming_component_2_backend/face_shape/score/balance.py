"""Vertical thirds and horizontal fifths on roll-corrected landmarks.

South Asian third means 0.31 / 0.34 / 0.35 are stored as unverified defaults
until the source tables are transcribed. Equal fifths use 0.20. Zygion is
the outer bound of the fifths, which sits slightly below the eye line.
"""

from dataclasses import dataclass

from face_shape.geometry import FrontalPoint, PreparedLandmarks, distance


THIRD_MEANS = (0.31, 0.34, 0.35)
FIFTH_MEAN = 0.20


@dataclass(frozen=True)
class BalanceResult:
    vertical_balance_score: float | None
    horizontal_balance_score: float | None
    balance_score: float | None
    thirds: dict[str, float]
    fifths: dict[str, float]
    notes: tuple[str, ...] = ()


def score_balance(prepared: PreparedLandmarks) -> BalanceResult:
    points = prepared.points
    notes: list[str] = []
    thirds, vertical, vertical_notes = _vertical(points)
    notes.extend(vertical_notes)
    fifths, horizontal, horizontal_notes = _horizontal(points)
    notes.extend(horizontal_notes)

    available = [value for value in (vertical, horizontal) if value is not None]
    combined = sum(available) / len(available) if available else None
    return BalanceResult(
        vertical_balance_score=vertical,
        horizontal_balance_score=horizontal,
        balance_score=combined,
        thirds=thirds,
        fifths=fifths,
        notes=tuple(notes),
    )


def _vertical(
    points: dict[str, FrontalPoint],
) -> tuple[dict[str, float], float | None, list[str]]:
    glabella = points.get("glabella")
    subnasale = points.get("subnasale")
    menton = points.get("menton")
    trichion = points.get("trichion")
    if glabella is None or subnasale is None or menton is None:
        return {}, None, ["vertical_landmarks_missing"]

    mid = distance(glabella, subnasale)
    lower = distance(subnasale, menton)
    if trichion is None:
        span = mid + lower
        if span <= 1e-9:
            return {}, None, ["limited_upper_third", "vertical_span_zero"]
        observed = mid / span
        reference = THIRD_MEANS[1] / (THIRD_MEANS[1] + THIRD_MEANS[2])
        score = max(0.0, 1.0 - abs(observed - reference) / reference)
        return {"p2_of_lower_face": observed}, score, ["limited_upper_third"]

    total = distance(trichion, menton)
    if total <= 1e-9:
        return {}, None, ["vertical_span_zero"]
    fractions = (
        distance(trichion, glabella) / total,
        mid / total,
        lower / total,
    )
    deviation = sum(abs(value - mean) / mean for value, mean in zip(fractions, THIRD_MEANS, strict=True))
    score = max(0.0, 1.0 - deviation / 3.0)
    labelled = {"p1": fractions[0], "p2": fractions[1], "p3": fractions[2]}
    return labelled, score, []


def _horizontal(
    points: dict[str, FrontalPoint],
) -> tuple[dict[str, float], float | None, list[str]]:
    needed = (
        "zygion_r",
        "exocanthion_r",
        "endocanthion_r",
        "endocanthion_l",
        "exocanthion_l",
        "zygion_l",
    )
    if any(points.get(name) is None for name in needed):
        return {}, None, ["horizontal_landmarks_missing"]
    width = distance(points["zygion_l"], points["zygion_r"])
    if width <= 1e-9:
        return {}, None, ["horizontal_span_zero"]
    segments = (
        distance(points["zygion_r"], points["exocanthion_r"]) / width,
        distance(points["exocanthion_r"], points["endocanthion_r"]) / width,
        distance(points["endocanthion_r"], points["endocanthion_l"]) / width,
        distance(points["endocanthion_l"], points["exocanthion_l"]) / width,
        distance(points["exocanthion_l"], points["zygion_l"]) / width,
    )
    deviation = sum(abs(value - FIFTH_MEAN) / FIFTH_MEAN for value in segments)
    score = max(0.0, 1.0 - deviation / 5.0)
    labelled = {f"s{index}": value for index, value in enumerate(segments, start=1)}
    return labelled, score, []
