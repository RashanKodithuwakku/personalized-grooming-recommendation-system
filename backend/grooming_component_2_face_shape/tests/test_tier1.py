import pytest

from face_shape.contracts import JawTypeObservation
from face_shape.rules import hard_threshold_label, morphological_class
from face_shape.tier1 import classify_tier1
from tests.helpers import face


@pytest.mark.parametrize(
    ("mfi", "jmi", "fzi", "expected"),
    [
        (87.0, 78.0, 78.0, "oval"),
        (87.0, 90.0, 86.0, "square"),
        (80.0, 78.0, 80.0, "round"),
        (100.0, 78.0, 80.0, "oblong"),
        (87.0, 65.0, 88.0, "heart"),
        (87.0, 65.0, 65.0, "diamond"),
    ],
)
def test_core_indices_select_the_matching_class(mfi, jmi, fzi, expected):
    result = classify_tier1(face(mfi, jmi, fzi))
    assert result.face_type == expected
    assert result.baseline_label == expected
    assert result.face_type_confidence[expected] == max(result.face_type_confidence.values())
    assert sum(result.face_type_confidence.values()) == pytest.approx(1.0)
    assert result.modifiers_applied == []


def test_wide_jaw_short_face_is_square_not_round():
    result = classify_tier1(face(75.0, 90.0, 86.0))
    assert result.face_type == "square"
    assert result.baseline_label == "square"


def test_mfi_ninety_is_oblong_not_heart():
    result = classify_tier1(face(90.0, 65.0, 88.0))
    assert result.face_type == "oblong"
    assert result.baseline_label == "oblong"


def test_mid_fzi_narrow_jaw_splits_heart_and_diamond():
    heart = classify_tier1(face(87.0, 65.0, 76.0))
    diamond = classify_tier1(face(87.0, 72.0, 76.0))
    assert heart.face_type == "heart"
    assert diamond.face_type == "diamond"


def test_missing_fzi_does_not_guess_heart_or_diamond():
    result = classify_tier1(face(87.0, 65.0, fzi=None))
    assert result.face_type not in {"heart", "diamond"}
    assert "narrow_jaw_unresolved" in result.processing_notes
    assert result.baseline_label is None


def test_morphological_bands():
    assert morphological_class(79.0) == "Hypereuryprosopic"
    assert morphological_class(82.0) == "Euryprosopic"
    assert morphological_class(87.0) == "Mesoprosopic"
    assert morphological_class(92.0) == "Leptoprosopic"
    assert morphological_class(96.0) == "Hyperleptoprosopic"


def test_depth_does_not_change_the_tier1_label():
    flat = classify_tier1(face(87.0, 78.0, 78.0))
    spatial = classify_tier1(face(87.0, 78.0, 78.0, z=-12.0))
    assert spatial.face_type == flat.face_type
    assert spatial.face_shape_class == "Mesoprosopic"


def test_jaw_type_is_retained_without_changing_the_class():
    sample = face(87.0, 83.0, 83.0)
    sample.jaw_type = JawTypeObservation(label="angular", confidence=0.9)
    untouched = classify_tier1(face(87.0, 83.0, 83.0))
    observed = classify_tier1(sample)
    assert observed.face_type == untouched.face_type
    assert observed.jaw_type is not None
    assert observed.modifiers_applied == []


def test_hard_baseline_uses_locked_cuts():
    notes: list[str] = []
    from face_shape.contracts import RatioFeatures

    assert hard_threshold_label(RatioFeatures(mfi=91.0, jmi=70.0, fzi=80.0), notes) == "oblong"
    assert hard_threshold_label(RatioFeatures(mfi=87.0, jmi=84.0, fzi=80.0), notes) == "square"
    assert hard_threshold_label(RatioFeatures(mfi=80.0, jmi=78.0, fzi=80.0), notes) == "round"
    assert hard_threshold_label(RatioFeatures(mfi=87.0, jmi=78.0, fzi=80.0), notes) == "oval"
    assert hard_threshold_label(RatioFeatures(mfi=87.0, jmi=70.0, fzi=88.0), notes) == "heart"
    assert hard_threshold_label(RatioFeatures(mfi=87.0, jmi=70.0, fzi=70.0), notes) == "diamond"
