"""Trapezoidal class intervals for the locked production rules.

Core plateaus follow Section 8 of the Component 2 handover:
Oblong MFI >= 90, Square JMI > 83 with MFI < 90, Round MFI < 85 and
JMI 75-83, Oval MFI 85-89.9 and JMI 75-83, Heart/Diamond JMI < 75.
The literature cut JMI < 72 is kept only as LITERATURE_NARROW_JMI.
"""

from dataclasses import dataclass

from face_shape.contracts import FaceShapeName


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


# Production JMI cut between Round/Oval and Heart/Diamond. Literature used 72.
NARROW_JMI = 75.0
LITERATURE_NARROW_JMI = 72.0
SQUARE_JMI = 83.0
OBLONG_MFI = 90.0
OVAL_MFI_LOW = 85.0
OVAL_MFI_HIGH = 89.9
HEART_FZI = 78.0
DIAMOND_FZI = 75.0
FZI_BROAD = 82.0
FZI_NARROW = 75.0

CLASS_TRAPEZOIDS: dict[FaceShapeName, dict[str, Trapezoid]] = {
    "oval": {
        "mfi": Trapezoid(80.0, 85.0, 89.9, 93.0),
        "jmi": Trapezoid(70.0, 75.0, 83.0, 87.0),
    },
    "round": {
        "mfi": Trapezoid(c=85.0, d=90.0),
        "jmi": Trapezoid(70.0, 75.0, 83.0, 87.0),
    },
    "square": {
        "mfi": Trapezoid(c=90.0, d=95.0),
        "jmi": Trapezoid(75.0, 83.0),
    },
    "oblong": {
        "mfi": Trapezoid(a=85.0, b=90.0),
    },
    "heart": {
        "jmi": Trapezoid(c=75.0, d=83.0),
        "fzi": Trapezoid(a=70.0, b=75.0),
    },
    "diamond": {
        "jmi": Trapezoid(c=75.0, d=83.0),
        "fzi": Trapezoid(c=75.0, d=78.0),
    },
}

# Total face height / bizygomatic. Typical faces sit near 1.30-1.45.
TFI_OBLONG = Trapezoid(a=1.40, b=1.55)
OVAL_TFI_PENALTY = 0.35

# Jaw-type weight peaks at the JMI 83 Square vs Round/Oval boundary.
JAW_TIE_BAND = Trapezoid(79.0, 83.0, 83.0, 87.0)


def class_features(name: FaceShapeName) -> tuple[str, ...]:
    return tuple(CLASS_TRAPEZOIDS[name])
