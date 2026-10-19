"""Hard-threshold baseline and Martin-Saller morphological class."""

from face_shape.contracts import FaceShapeName, MorphologicalClass, RatioFeatures
from face_shape.thresholds import OBLONG_MFI, OVAL_MFI_LOW, SQUARE_JMI, NARROW_JMI


def morphological_class(mfi: float) -> MorphologicalClass:
    if mfi < 80.0:
        return "Hypereuryprosopic"
    if mfi < 85.0:
        return "Euryprosopic"
    if mfi < 90.0:
        return "Mesoprosopic"
    if mfi < 95.0:
        return "Leptoprosopic"
    return "Hyperleptoprosopic"


def hard_threshold_label(ratios: RatioFeatures, notes: list[str]) -> FaceShapeName | None:
    """Marinescu-style evaluation baseline. Does not replace production scores."""

    if ratios.mfi is None or ratios.jmi is None:
        return None
    mfi = ratios.mfi
    jmi = ratios.jmi
    fzi = ratios.fzi

    if mfi >= OBLONG_MFI:
        return "oblong"
    if jmi > SQUARE_JMI and mfi < OBLONG_MFI:
        if fzi is not None and fzi < jmi - 6.0:
            notes.append("triangle_mapped_to_square")
        return "square"
    if NARROW_JMI <= jmi <= SQUARE_JMI and mfi < OVAL_MFI_LOW:
        return "round"
    if NARROW_JMI <= jmi <= SQUARE_JMI and OVAL_MFI_LOW <= mfi < OBLONG_MFI:
        if fzi is not None and fzi < jmi - 3.0:
            notes.append("oval_fzi_note")
        return "oval"
    if jmi < NARROW_JMI:
        if fzi is None:
            notes.append("narrow_jaw_unresolved")
            return None
        if fzi >= 78.0 and fzi >= jmi + 6.0:
            return "heart"
        if fzi < 75.0:
            return "diamond"
        return "heart" if (fzi - jmi) >= 6.0 else "diamond"
    return None
