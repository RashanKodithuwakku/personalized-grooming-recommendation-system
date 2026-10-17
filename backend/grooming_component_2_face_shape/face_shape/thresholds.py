"""Trapezoidal class intervals for MFI, JMI, and FZI.

Plateaus follow the published bands: Martin mesoprosopic MFI 85.0-89.9,
Farkas oval JMI and FZI near 75-82, Marinescu square jaw at JMI 83, and the
narrow-jaw band below JMI 72. Each ramp is the soft boundary around that
band. The JMI ramps of oval, round, and square meet across 81-85, which is
the jaw-type tie region used by the second tier.
"""

from dataclasses import dataclass

from face_shape.contracts import FACE_SHAPES, FaceShapeName


@dataclass(frozen=True)
class Trapezoid:
    """Membership plateau on [b, c], with feet at a and d.

    A missing foot and shoulder on one side leaves that side open, so the
    plateau continues to infinity.
    """

    a: float | None = None
    b: float | None = None
    c: float | None = None
    d: float | None = None

    def __post_init__(self) -> None:
        _require_pair(self.a, self.b, "left")
        _require_pair(self.c, self.d, "right")
        ordered = [value for value in (self.a, self.b, self.c, self.d) if value is not None]
        if ordered != sorted(ordered):
            raise ValueError("trapezoid shoulders must be ordered")
        if self.a is not None and self.b is not None and self.a == self.b:
            raise ValueError("left ramp has no width")
        if self.c is not None and self.d is not None and self.c == self.d:
            raise ValueError("right ramp has no width")


def _require_pair(foot: float | None, shoulder: float | None, side: str) -> None:
    if (foot is None) != (shoulder is None):
        raise ValueError(f"{side} trapezoid edge needs both foot and shoulder")


CLASS_TRAPEZOIDS: dict[FaceShapeName, dict[str, Trapezoid]] = {
    "oval": {
        "mfi": Trapezoid(80.0, 85.0, 89.9, 95.0),
        "jmi": Trapezoid(72.0, 75.0, 81.0, 85.0),
        "fzi": Trapezoid(71.0, 75.0, 82.0, 86.0),
    },
    "round": {
        "mfi": Trapezoid(c=80.0, d=88.0),
        "jmi": Trapezoid(78.0, 86.0, 98.0, 106.0),
        "fzi": Trapezoid(74.0, 80.0, 92.0, 98.0),
    },
    "square": {
        "mfi": Trapezoid(76.0, 82.0, 92.0, 98.0),
        "jmi": Trapezoid(81.0, 85.0, 98.0, 106.0),
        "fzi": Trapezoid(74.0, 80.0, 92.0, 98.0),
    },
    "oblong": {
        "mfi": Trapezoid(a=90.0, b=97.0),
        "jmi": Trapezoid(68.0, 74.0, 84.0, 90.0),
        "fzi": Trapezoid(70.0, 75.0, 86.0, 92.0),
    },
    "heart": {
        "mfi": Trapezoid(78.0, 84.0, 96.0, 104.0),
        "jmi": Trapezoid(c=70.0, d=76.0),
        "fzi": Trapezoid(74.0, 80.0, 96.0, 102.0),
    },
    "diamond": {
        "mfi": Trapezoid(78.0, 84.0, 96.0, 104.0),
        "jmi": Trapezoid(c=70.0, d=76.0),
        "fzi": Trapezoid(c=72.0, d=78.0),
    },
}


def _coverage() -> None:
    for name in FACE_SHAPES:
        features = CLASS_TRAPEZOIDS[name]
        if set(features) != {"mfi", "jmi", "fzi"}:
            raise ValueError(f"{name} is missing a tier-1 feature interval")


_coverage()
