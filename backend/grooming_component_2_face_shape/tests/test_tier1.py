import pytest

from face_shape.contracts import ClassificationInput, JawTypeObservation, LandmarkPoint, Tier1Landmarks, Tier2Landmarks
from face_shape.tier1 import classify_tier1


def _point(x: float, y: float, z: float | None = None) -> LandmarkPoint:
    payload = {"x": x, "y": y}
    if z is not None:
        payload["z"] = z
    return LandmarkPoint.model_validate(payload)


def _face(mfi: float, jmi: float, fzi: float, z: float | None = None) -> ClassificationInput:
    return ClassificationInput(
        tier1=Tier1Landmarks(
            nasion=_point(0.0, 0.0, z),
            menton=_point(0.0, mfi, z),
            zygion_left=_point(-50.0, 40.0, z),
            zygion_right=_point(50.0, 40.0, z),
            gonion_left=_point(-jmi / 2.0, 70.0, z),
            gonion_right=_point(jmi / 2.0, 70.0, z),
            frontotemporale_left=_point(-fzi / 2.0, 15.0, z),
            frontotemporale_right=_point(fzi / 2.0, 15.0, z),
        ),
        tier2=Tier2Landmarks(),
    )


@pytest.mark.parametrize(
    ("mfi", "jmi", "fzi", "expected"),
    [
        (87.0, 78.0, 78.0, "oval"),
        (87.0, 90.0, 86.0, "square"),
        (75.0, 90.0, 86.0, "round"),
        (100.0, 78.0, 80.0, "oblong"),
        (90.0, 65.0, 88.0, "heart"),
        (90.0, 65.0, 65.0, "diamond"),
    ],
)
def test_core_indices_select_the_matching_class(mfi, jmi, fzi, expected):
    result = classify_tier1(_face(mfi, jmi, fzi))

    assert result.face_type == expected
    assert result.face_type_confidence[expected] == max(result.face_type_confidence.values())
    assert sum(result.face_type_confidence.values()) == pytest.approx(1.0)
    assert result.modifiers_applied == []
    assert result.ratios.tfi is None


def test_depth_does_not_change_the_tier1_label():
    flat = classify_tier1(_face(87.0, 78.0, 78.0))
    spatial = classify_tier1(_face(87.0, 78.0, 78.0, z=-12.0))

    assert spatial.face_type == flat.face_type
    assert spatial.face_type_confidence == pytest.approx(flat.face_type_confidence)


def test_jaw_type_is_retained_without_changing_the_class():
    sample = _face(87.0, 83.0, 78.0)
    sample.jaw_type = JawTypeObservation(label="angular", confidence=0.9)
    untouched = classify_tier1(_face(87.0, 83.0, 78.0))
    observed = classify_tier1(sample)

    assert observed.face_type == untouched.face_type
    assert observed.jaw_type is not None
    assert observed.jaw_type.label == "angular"
    assert observed.modifiers_applied == []
