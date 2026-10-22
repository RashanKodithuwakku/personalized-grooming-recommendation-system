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


# Bilateral pairs. The right point is reflected across the midline and
# compared with the left point.
PAIR_NAMES: tuple[str, ...] = (
    "endocanthion",
    "exocanthion",
    "alare",
    "cheilion",
    "gonion",
)
# Midline landmarks. Their distance to the line is the deviation,
# because reflecting them would hide a shift of the jaw or nose.
MIDLINE_TERMS: tuple[str, ...] = ("subnasale", "menton")
# Mouth is down-weighted even at rest, and again if the expression
# is not neutral, because lips move more than bone landmarks.
DEFAULT_WEIGHTS: dict[str, float] = {
    "endocanthion": 1.0,
    "exocanthion": 1.0,
    "alare": 1.0,
    "cheilion": 0.5,
    "gonion": 1.0,
    "subnasale": 1.0,
    "menton": 1.0,
}
# Asymmetry index of 5 percent of face width maps to a symmetry score of 0.
AI_MAX = 5.0
# Yaw past this angle does not change the number; it adds a limited note.
YAW_LIMIT = 5.0
# Mouth weight used when Component 1 says the expression is not neutral.
CHEILION_EXPRESSION_WEIGHT = 0.25


# One landmark's deviation in pixels, the weight used, and signed offsets
# to the subject's right. Offsets let the frontend show which side is out.
class PairDeviation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    deviation: float
    weight: float
    left_offset: float | None = None
    right_offset: float | None = None


# symmetry_score is 0-1 for the frontend. asymmetry_index is the
# percentage form (100 * mean deviation / bizygomatic breadth).
@dataclass(frozen=True)
class SymmetryResult:
    symmetry_score: float | None
    asymmetry_index: float | None
    per_pair_deviations: list[PairDeviation]
    notes: tuple[str, ...] = ()


# Build the midline, average the weighted deviations, scale by face
# width, then clip 1 - AI/5 into the unit interval.
def score_symmetry(
    prepared: PreparedLandmarks,
    yaw: float | None = None,
    neutral_expression: bool = True,
) -> SymmetryResult:
    # Without a midline or a face width the score is withheld rather
    # than reported as a perfect or zero face.
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

    # Reflect each right point onto the left side and measure the gap.
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

    # Nose base and chin: perpendicular distance to the midline.
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

    # Mean absolute deviation over bizygomatic breadth, as a percentage.
    # Score falls linearly and reaches 0 when that percentage hits AI_MAX.
    mad = weighted / weight_sum
    asymmetry_index = (mad / bizygomatic) * 100.0
    score = max(0.0, min(1.0, 1.0 - asymmetry_index / AI_MAX))
    if yaw is not None and abs(yaw) > YAW_LIMIT:
        notes.append("symmetry_pose_limited")
    return SymmetryResult(score, asymmetry_index, deviations, tuple(notes))


# Midline origin is nasion. Direction is perpendicular to the eye line
# and pointed toward menton. rightward is the subject's right.
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


# Householder reflection of one point across the midline.
def reflect_across_line(point: FrontalPoint, origin: FrontalPoint, axis: FrontalPoint) -> FrontalPoint:
    rel = FrontalPoint(x=point.x - origin.x, y=point.y - origin.y)
    along = rel.x * axis.x + rel.y * axis.y
    return FrontalPoint(
        x=origin.x + 2.0 * along * axis.x - rel.x,
        y=origin.y + 2.0 * along * axis.y - rel.y,
    )


# Positive when the point lies to the subject's right of the midline.
def _signed_offset(point: FrontalPoint, origin: FrontalPoint, rightward: FrontalPoint) -> float:
    return (point.x - origin.x) * rightward.x + (point.y - origin.y) * rightward.y


# Unit vector, or None when the two points that formed it coincide.
def _unit(vector: FrontalPoint) -> FrontalPoint | None:
    length = (vector.x * vector.x + vector.y * vector.y) ** 0.5
    if length <= 1e-12:
        return None
    return FrontalPoint(x=vector.x / length, y=vector.y / length)


# Face-width normaliser. A zero width makes the asymmetry index undefined.
def _bizygomatic(points: dict[str, FrontalPoint]) -> float | None:
    left = points.get("zygion_l")
    right = points.get("zygion_r")
    if left is None or right is None:
        return None
    width = distance(left, right)
    return width if width > 1e-9 else None
