"""Frontal-plane landmarks for ratio measurement.

Component 1 may send image pixels or three-dimensional points. The indices
used here are frontal breadths and heights, so every point is reduced to the
supplied x-y plane before any distance is taken. Depth is not part of the
ratio. Pixel units and normalised units are left unchanged, because a ratio
cancels a shared scale.
"""

from dataclasses import dataclass
from typing import Literal

from face_shape.contracts import CORE_LANDMARKS, ClassificationInput, LandmarkPoint


CoordinateFrame = Literal["image_2d", "projected_3d", "partial_depth"]
CoordinateScale = Literal["pixel", "normalized"]

_NORMALIZED_LIMIT = 1.5


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


def prepare_landmarks(sample: ClassificationInput) -> PreparedLandmarks:
    """Project one Component 1 sample onto the frontal plane."""

    named = _named_points(sample)
    frame = _frame(named)
    scale = _scale(named)
    frontal = {name: to_frontal(point) for name, point in named.items()}
    return PreparedLandmarks(
        frame=frame,
        scale=scale,
        points={name: frontal[name] for name in CORE_LANDMARKS},
        trichion=frontal.get("trichion"),
    )


def to_frontal(point: LandmarkPoint) -> FrontalPoint:
    """Keep the frontal axes of a pixel point or a three-dimensional point."""

    return FrontalPoint(x=point.x, y=point.y)


def distance(start: FrontalPoint, end: FrontalPoint) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    return (dx * dx + dy * dy) ** 0.5


def _named_points(sample: ClassificationInput) -> dict[str, LandmarkPoint]:
    tier1 = sample.tier1
    named = {name: getattr(tier1, name) for name in CORE_LANDMARKS}
    if sample.tier2.trichion is not None:
        named["trichion"] = sample.tier2.trichion
    return named


def _frame(named: dict[str, LandmarkPoint]) -> CoordinateFrame:
    present = [point.z is not None for point in named.values()]
    if all(present):
        return "projected_3d"
    if any(present):
        return "partial_depth"
    return "image_2d"


def _scale(named: dict[str, LandmarkPoint]) -> CoordinateScale:
    peak = max(max(abs(point.x), abs(point.y)) for point in named.values())
    if peak > _NORMALIZED_LIMIT:
        return "pixel"
    return "normalized"
