import pytest

from face_shape.contracts import ClassificationInput, JawTypeObservation, LandmarkPoint, Tier1Landmarks, Tier2Landmarks
from face_shape.tier1 import classify_tier1
from face_shape.tier2 import classify_face


def _point(x: float, y: float) -> LandmarkPoint:
    return LandmarkPoint.model_validate({"x": x, "y": y})


def _face(
    mfi: float,
    jmi: float,
    fzi: float,
    tfi: float | None = None,
    jaw: str | None = None,
    jaw_confidence: float = 1.0,
) -> ClassificationInput:
    tier2 = Tier2Landmarks()
    if tfi is not None:
        tier2 = Tier2Landmarks(trichion=_point(0.0, mfi - (tfi * 100.0)))
    jaw_type = None
    if jaw is not None:
        jaw_type = JawTypeObservation(label=jaw, confidence=jaw_confidence)
    return ClassificationInput(
        tier1=Tier1Landmarks(
            nasion=_point(0.0, 0.0),
            menton=_point(0.0, mfi),
            zygion_left=_point(-50.0, 40.0),
            zygion_right=_point(50.0, 40.0),
            gonion_left=_point(-jmi / 2.0, 70.0),
            gonion_right=_point(jmi / 2.0, 70.0),
            frontotemporale_left=_point(-fzi / 2.0, 15.0),
            frontotemporale_right=_point(fzi / 2.0, 15.0),
        ),
        tier2=tier2,
        jaw_type=jaw_type,
    )


def test_without_modifiers_the_label_matches_tier1():
    sample = _face(87.0, 78.0, 78.0)
    assert classify_face(sample).face_type == classify_tier1(sample).face_type
    assert classify_face(sample).modifiers_applied == []


def test_high_total_face_ratio_selects_oblong():
    sample = _face(87.0, 78.0, 84.0, tfi=1.60)
    result = classify_face(sample)

    assert result.face_type == "oblong"
    assert result.modifiers_applied == ["tfi"]
    assert result.ratios.tfi == pytest.approx(1.60)


def test_typical_total_face_ratio_does_not_apply():
    sample = _face(87.0, 78.0, 84.0, tfi=1.30)
    result = classify_face(sample)

    assert result.modifiers_applied == []
    assert result.face_type == classify_tier1(sample).face_type


def test_angular_jaw_in_the_tie_band_selects_square():
    sample = _face(87.0, 83.0, 78.0, jaw="angular")
    result = classify_face(sample)

    assert classify_tier1(sample).face_type == "oval"
    assert result.face_type == "square"
    assert result.modifiers_applied == ["jaw_type"]


def test_rounded_jaw_in_the_tie_band_keeps_the_rounder_class():
    sample = _face(78.0, 83.0, 86.0, jaw="rounded")
    result = classify_face(sample)

    assert result.face_type == "round"
    assert result.modifiers_applied == ["jaw_type"]


def test_jaw_outside_the_tie_band_is_not_applied():
    sample = _face(87.0, 90.0, 86.0, jaw="angular")
    result = classify_face(sample)

    assert result.face_type == "square"
    assert result.modifiers_applied == []


def test_tapered_jaw_does_not_move_the_scores():
    plain = _face(87.0, 83.0, 78.0)
    tapered = _face(87.0, 83.0, 78.0, jaw="tapered")

    assert classify_face(tapered).face_type == classify_face(plain).face_type
    assert classify_face(tapered).modifiers_applied == []


def test_both_modifiers_are_recorded_in_order():
    sample = _face(87.0, 83.0, 84.0, tfi=1.60, jaw="angular", jaw_confidence=0.0)
    # Zero jaw confidence must not count as an applied jaw modifier.
    assert classify_face(sample).modifiers_applied == ["tfi"]

    moved = _face(87.0, 83.0, 84.0, tfi=1.60, jaw="angular")
    assert classify_face(moved).modifiers_applied == ["tfi", "jaw_type"]
