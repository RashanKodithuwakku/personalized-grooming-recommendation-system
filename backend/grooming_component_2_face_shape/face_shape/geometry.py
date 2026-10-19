"""Frontal-plane landmarks for ratio measurement.

Normalised coordinates are converted to pixels with the reported image size
before any distance is taken. Depth is dropped. Paired points are then
rotated so the eye line is horizontal, or so nasion-menton is vertical when
the eyes are absent.
"""

from dataclasses import dataclass
from math import atan2, cos, pi, sin
from typing import Literal

from face_shape.contracts import (
    CORE_LANDMARKS,
    ClassificationInput,
    LandmarkPoint,
    usable_point,
)


CoordinateFrame = Literal["image_2d", "projected_3d", "partial_depth"]
CoordinateScale = Literal["pixel", "normalized"]


@dataclass(frozen=True)
class FrontalPoint:
    x: float
    y: float


@dataclass(frozen=True)
class PreparedLandmarks:
    frame: CoordinateFrame
    scale: CoordinateScale
    points: dict[str, FrontalPoint]
    trichion: FrontalPoint | None
    roll_corrected: bool


def prepare_landmarks(sample: ClassificationInput) -> PreparedLandmarks:
    """Project one Component 1 sample onto the frontal pixel plane."""

    named = _named_points(sample)
    frame = _frame(named)
    scale: CoordinateScale = "pixel"
    if sample.image is not None:
        scale = sample.image.coordinate_mode
    else:
        scale = _inferred_scale(named)

    frontal: dict[str, FrontalPoint] = {}
    for name, point in named.items():
        usable = usable_point(point)
        if usable is None:
            continue
        frontal[name] = to_pixels(usable, sample)

    frontal, rolled = roll_correct(frontal)
    core = {name: frontal[name] for name in CORE_LANDMARKS if name in frontal}
    return PreparedLandmarks(
        frame=frame,
        scale=scale,
        points=core | {name: point for name, point in frontal.items() if name not in core},
        trichion=frontal.get("trichion"),
        roll_corrected=rolled,
    )


def to_pixels(point: LandmarkPoint, sample: ClassificationInput) -> FrontalPoint:
    """Keep pixel coordinates; expand normalised coordinates with image size."""

    assert point.x is not None and point.y is not None
    image = sample.image
    if image is not None and image.coordinate_mode == "normalized":
        return FrontalPoint(x=point.x * image.width, y=point.y * image.height)
    return FrontalPoint(x=point.x, y=point.y)


def to_frontal(point: LandmarkPoint) -> FrontalPoint:
    """Keep the frontal axes of a pixel point or a three-dimensional point."""

    assert point.x is not None and point.y is not None
    return FrontalPoint(x=point.x, y=point.y)


def distance(start: FrontalPoint, end: FrontalPoint) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    return (dx * dx + dy * dy) ** 0.5


def roll_correct(points: dict[str, FrontalPoint]) -> tuple[dict[str, FrontalPoint], bool]:
    """Rotate so the intercanthal line is horizontal when both eyes exist."""

    left = points.get("endocanthion_l")
    right = points.get("endocanthion_r")
    if left is not None and right is not None:
        angle = -atan2(left.y - right.y, left.x - right.x)
        origin = FrontalPoint(x=(left.x + right.x) / 2.0, y=(left.y + right.y) / 2.0)
        return _rotate_all(points, origin, angle), True

    nasion = points.get("nasion")
    menton = points.get("menton")
    if nasion is None or menton is None:
        return points, False
    current = atan2(menton.y - nasion.y, menton.x - nasion.x)
    angle = (pi / 2.0) - current
    return _rotate_all(points, nasion, angle), True


def _rotate_all(
    points: dict[str, FrontalPoint], origin: FrontalPoint, angle: float
) -> dict[str, FrontalPoint]:
    if abs(angle) < 1e-12:
        return points
    cosine = cos(angle)
    sine = sin(angle)
    rotated: dict[str, FrontalPoint] = {}
    for name, point in points.items():
        dx = point.x - origin.x
        dy = point.y - origin.y
        rotated[name] = FrontalPoint(
            x=origin.x + dx * cosine - dy * sine,
            y=origin.y + dx * sine + dy * cosine,
        )
    return rotated


def _named_points(sample: ClassificationInput) -> dict[str, LandmarkPoint]:
    named: dict[str, LandmarkPoint] = {}
    for name in CORE_LANDMARKS:
        point = getattr(sample.tier1, name)
        if point is not None:
            named[name] = point
    if sample.tier2.trichion is not None:
        named["trichion"] = sample.tier2.trichion
    named.update(sample.extra)
    return named


def _frame(named: dict[str, LandmarkPoint]) -> CoordinateFrame:
    usable = [point for point in named.values() if usable_point(point) is not None]
    present = [point.z is not None for point in usable]
    if present and all(present):
        return "projected_3d"
    if any(present):
        return "partial_depth"
    return "image_2d"


def _inferred_scale(named: dict[str, LandmarkPoint]) -> CoordinateScale:
    usable = [point for point in named.values() if usable_point(point) is not None]
    if not usable:
        return "pixel"
    peak = max(max(abs(point.x or 0.0), abs(point.y or 0.0)) for point in usable)
    if peak > 1.5:
        return "pixel"
    return "normalized"
