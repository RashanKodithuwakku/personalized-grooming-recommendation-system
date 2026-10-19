"""Facial asymmetry index on roll-corrected frontal landmarks.

The midline passes through nasion and is perpendicular to the intercanthal
line. Each bilateral pair is scored by reflecting the subject's right point
across that line and taking the 2D distance to the left counterpart.
Subnasale and menton contribute their perpendicular distances to the same
line so jaw deviation is measured rather than absorbed into the axis.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from face_shape.geometry import FrontalPoint, PreparedLandmarks, distance


PAIR_NAMES: tuple[str, ...] = (
    "endocanthion",
    "exocanthion",
    "alare",
    "cheilion",
    "gonion",
)
MIDLINE_TERMS: tuple[str, ...] = ("subnasale", "menton")
DEFAULT_WEIGHTS: dict[str, float] = {
    "endocanthion": 1.0,
    "exocanthion": 1.0,
    "alare": 1.0,
    "cheilion": 0.5,
    "gonion": 1.0,
    "subnasale": 1.0,
    "menton": 1.0,
}
AI_MAX = 5.0
YAW_LIMIT = 5.0
CHEILION_EXPRESSION_WEIGHT = 0.25


class PairDeviation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    deviation: float
    weight: float
    left_offset: float | None = None
    right_offset: float | None = None


@dataclass(frozen=True)
class SymmetryResult:
    symmetry_score: float | None
    asymmetry_index: float | None
    per_pair_deviations: list[PairDeviation]
    notes: tuple[str, ...] = ()


def score_symmetry(
    prepared: PreparedLandmarks,
    yaw: float | None = None,
    neutral_expression: bool = True,
) -> SymmetryResult:
    points = prepared.points
    notes: list[str] = []
    midline = build_midline(points)
    if midline is None:
        return SymmetryResult(None, None, [], ("symmetry_midline_unavailable",))

    bizygomatic = _bizygomatic(points)
    if bizygomatic is None:
        return SymmetryResult(None, None, [], ("symmetry_width_unavailable",))

    weights = dict(DEFAULT_WEIGHTS)
    if not neutral_expression:
        weights["cheilion"] = CHEILION_EXPRESSION_WEIGHT
        notes.append("mouth_downweighted")

    deviations: list[PairDeviation] = []
    weighted = 0.0
    weight_sum = 0.0
    origin, axis, rightward = midline

    for name in PAIR_NAMES:
        left = points.get(f"{name}_l")
        right = points.get(f"{name}_r")
        if left is None or right is None:
            continue
        reflected = reflect_across_line(right, origin, axis)
        deviation = distance(reflected, left)
        weight = weights[name]
        deviations.append(
            PairDeviation(
                name=name,
                deviation=deviation,
                weight=weight,
                left_offset=_signed_offset(left, origin, rightward),
                right_offset=_signed_offset(right, origin, rightward),
            )
        )
        weighted += weight * deviation
        weight_sum += weight

    for name in MIDLINE_TERMS:
        point = points.get(name)
        if point is None:
            continue
        deviation = abs(_signed_offset(point, origin, rightward))
        weight = weights[name]
        deviations.append(
            PairDeviation(name=name, deviation=deviation, weight=weight, left_offset=deviation)
        )
        weighted += weight * deviation
        weight_sum += weight

    if weight_sum <= 0.0:
        return SymmetryResult(None, None, deviations, tuple(notes + ["symmetry_pairs_missing"]))

    mad = weighted / weight_sum
    asymmetry_index = (mad / bizygomatic) * 100.0
    score = max(0.0, min(1.0, 1.0 - asymmetry_index / AI_MAX))
    if yaw is not None and abs(yaw) > YAW_LIMIT:
        notes.append("symmetry_pose_limited")
    return SymmetryResult(score, asymmetry_index, deviations, tuple(notes))


def build_midline(
    points: dict[str, FrontalPoint],
) -> tuple[FrontalPoint, FrontalPoint, FrontalPoint] | None:
    nasion = points.get("nasion")
    left = points.get("endocanthion_l")
    right = points.get("endocanthion_r")
    if nasion is None or left is None or right is None:
        return None
    eye = FrontalPoint(x=left.x - right.x, y=left.y - right.y)
    perp = _unit(FrontalPoint(x=-eye.y, y=eye.x))
    if perp is None:
        return None
    down = points.get("menton")
    if down is not None:
        toward = FrontalPoint(x=down.x - nasion.x, y=down.y - nasion.y)
        if toward.x * perp.x + toward.y * perp.y < 0.0:
            perp = FrontalPoint(x=-perp.x, y=-perp.y)
    rightward = _unit(FrontalPoint(x=eye.x, y=eye.y))
    if rightward is None:
        return None
    # eye vector is left minus right, so it points to the subject's left.
    rightward = FrontalPoint(x=-rightward.x, y=-rightward.y)
    return nasion, perp, rightward


def reflect_across_line(point: FrontalPoint, origin: FrontalPoint, axis: FrontalPoint) -> FrontalPoint:
    rel = FrontalPoint(x=point.x - origin.x, y=point.y - origin.y)
    along = rel.x * axis.x + rel.y * axis.y
    return FrontalPoint(
        x=origin.x + 2.0 * along * axis.x - rel.x,
        y=origin.y + 2.0 * along * axis.y - rel.y,
    )


def _signed_offset(point: FrontalPoint, origin: FrontalPoint, rightward: FrontalPoint) -> float:
    return (point.x - origin.x) * rightward.x + (point.y - origin.y) * rightward.y


def _unit(vector: FrontalPoint) -> FrontalPoint | None:
    length = (vector.x * vector.x + vector.y * vector.y) ** 0.5
    if length <= 1e-12:
        return None
    return FrontalPoint(x=vector.x / length, y=vector.y / length)


def _bizygomatic(points: dict[str, FrontalPoint]) -> float | None:
    left = points.get("zygion_l")
    right = points.get("zygion_r")
    if left is None or right is None:
        return None
    width = distance(left, right)
    return width if width > 1e-9 else None
