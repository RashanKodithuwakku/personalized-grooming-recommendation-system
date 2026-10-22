"""Builders for synthetic faces used by the unit tests.

point() makes one landmark. face() places zygion 100 units apart so the
requested MFI, JMI, and FZI become the measured percentage indices.
"""

from face_shape.contracts import (
    ClassificationInput,
    ImageSpec,
    JawTypeObservation,
    LandmarkPoint,
    Tier1Landmarks,
    Tier2Landmarks,
)


# One landmark. z is optional and is dropped later by the geometry step.
def point(x: float, y: float, z: float | None = None, visible: bool = True) -> LandmarkPoint:
    payload: dict[str, float | bool | None] = {"x": x, "y": y, "visible": visible}
    if z is not None:
        payload["z"] = z
    return LandmarkPoint.model_validate(payload)


# Build a face whose measured MFI, JMI, and FZI match the arguments,
# because bizygomatic breadth is fixed at 100.
def face(
    mfi: float,
    jmi: float,
    fzi: float | None = 78.0,
    tfi: float | None = None,
    jaw: str | None = None,
    jaw_confidence: float = 1.0,
    z: float | None = None,
    image: ImageSpec | None = None,
    scale: float = 1.0,
) -> ClassificationInput:
    def located(x: float, y: float, depth: float | None = z) -> LandmarkPoint:
        return point(x * scale, y * scale, depth)

    ft_l = located(-fzi / 2.0, 15.0) if fzi is not None else None
    ft_r = located(fzi / 2.0, 15.0) if fzi is not None else None
    tier2 = Tier2Landmarks()
    if tfi is not None:
        tier2 = Tier2Landmarks(trichion=located(0.0, mfi - (tfi * 100.0)))
    jaw_type = None
    if jaw is not None:
        jaw_type = JawTypeObservation(label=jaw, confidence=jaw_confidence)
    return ClassificationInput(
        tier1=Tier1Landmarks(
            nasion=located(0.0, 0.0),
            menton=located(0.0, mfi),
            zygion_l=located(-50.0, 40.0),
            zygion_r=located(50.0, 40.0),
            gonion_l=located(-jmi / 2.0, 70.0),
            gonion_r=located(jmi / 2.0, 70.0),
            frontotemporale_l=ft_l,
            frontotemporale_r=ft_r,
        ),
        tier2=tier2,
        jaw_type=jaw_type,
        image=image,
    )
