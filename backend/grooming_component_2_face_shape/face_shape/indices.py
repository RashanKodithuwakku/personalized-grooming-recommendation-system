"""Anthropometric indices on prepared frontal landmarks.

MFI, JMI, and FZI follow the percentage form used by Martin and Farkas:
100 * measurement / bizygomatic breadth. TFI stays a raw height-to-breadth
ratio because its operating range is about 1.30 for a typical face and about
1.55 where an oblong face begins.
"""

from face_shape.contracts import RatioFeatures
from face_shape.geometry import PreparedLandmarks, distance


_MIN_BREADTH = 1e-9


class DegenerateMeasurement(ValueError):
    """Raised when a landmark pair collapses and a ratio is undefined."""


def measure_ratios(prepared: PreparedLandmarks) -> RatioFeatures:
    points = prepared.points
    bizygomatic = distance(points["zygion_left"], points["zygion_right"])
    if bizygomatic <= _MIN_BREADTH:
        raise DegenerateMeasurement("bizygomatic breadth is zero")

    face_height = distance(points["nasion"], points["menton"])
    bigonial = distance(points["gonion_left"], points["gonion_right"])
    bitemporal = distance(points["frontotemporale_left"], points["frontotemporale_right"])
    tfi = None
    if prepared.trichion is not None:
        total_height = distance(prepared.trichion, points["menton"])
        tfi = total_height / bizygomatic

    return RatioFeatures(
        mfi=percentage_index(face_height, bizygomatic),
        jmi=percentage_index(bigonial, bizygomatic),
        fzi=percentage_index(bitemporal, bizygomatic),
        tfi=tfi,
    )


def percentage_index(measurement: float, bizygomatic: float) -> float:
    if bizygomatic <= _MIN_BREADTH:
        raise DegenerateMeasurement("bizygomatic breadth is zero")
    return 100.0 * measurement / bizygomatic
