"""Anthropometric indices on prepared frontal landmarks.

MFI, JMI, and FZI follow the percentage form used by Martin and Farkas:
100 * measurement / bizygomatic breadth. TFI stays a raw height-to-breadth
ratio because its operating range is about 1.30 for a typical face and about
1.55 where an oblong face begins. FZI is omitted when either frontotemporale
point is missing.
"""

from face_shape.contracts import RatioFeatures
from face_shape.geometry import PreparedLandmarks, distance


_MIN_BREADTH = 1e-9


class DegenerateMeasurement(ValueError):
    """Raised when a landmark pair collapses and a ratio is undefined."""


def measure_ratios(prepared: PreparedLandmarks) -> RatioFeatures:
    points = prepared.points
    left = points.get("zygion_l")
    right = points.get("zygion_r")
    nasion = points.get("nasion")
    menton = points.get("menton")
    gonion_l = points.get("gonion_l")
    gonion_r = points.get("gonion_r")
    if None in (left, right, nasion, menton, gonion_l, gonion_r):
        raise DegenerateMeasurement("required shape landmarks are missing")

    bizygomatic = distance(left, right)
    if bizygomatic <= _MIN_BREADTH:
        raise DegenerateMeasurement("bizygomatic breadth is zero")

    face_height = distance(nasion, menton)
    bigonial = distance(gonion_l, gonion_r)
    fzi = None
    ft_l = points.get("frontotemporale_l")
    ft_r = points.get("frontotemporale_r")
    if ft_l is not None and ft_r is not None:
        fzi = percentage_index(distance(ft_l, ft_r), bizygomatic)

    tfi = None
    if prepared.trichion is not None:
        tfi = distance(prepared.trichion, menton) / bizygomatic

    return RatioFeatures(
        mfi=percentage_index(face_height, bizygomatic),
        jmi=percentage_index(bigonial, bizygomatic),
        fzi=fzi,
        tfi=tfi,
    )


def percentage_index(measurement: float, bizygomatic: float) -> float:
    if bizygomatic <= _MIN_BREADTH:
        raise DegenerateMeasurement("bizygomatic breadth is zero")
    return 100.0 * measurement / bizygomatic
