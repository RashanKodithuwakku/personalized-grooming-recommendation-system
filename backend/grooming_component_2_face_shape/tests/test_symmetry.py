"""Symmetry on a mirrored face, a shifted jaw, and a large yaw.

A perfect mirror should score near 1. Moving gonion should lower it.
"""

from face_shape.contracts import ClassificationInput, LandmarkPoint, Tier1Landmarks
from face_shape.geometry import prepare_landmarks
from face_shape.score.symmetry import score_symmetry


# Pixel landmark with no depth.
def _pt(x: float, y: float) -> LandmarkPoint:
    return LandmarkPoint.model_validate({"x": x, "y": y, "visible": True})


# Bilateral points mirrored about x = 0. shift moves the left gonion only.
def _symmetric_sample(shift: float = 0.0) -> ClassificationInput:
    extra = {
        "endocanthion_r": _pt(-20.0, 40.0),
        "endocanthion_l": _pt(20.0, 40.0),
        "exocanthion_r": _pt(-40.0, 42.0),
        "exocanthion_l": _pt(40.0, 42.0),
        "alare_r": _pt(-12.0, 70.0),
        "alare_l": _pt(12.0, 70.0),
        "cheilion_r": _pt(-18.0, 90.0),
        "cheilion_l": _pt(18.0, 90.0),
        "glabella": _pt(0.0, 20.0),
        "subnasale": _pt(0.0, 72.0),
    }
    extra["gonion_l"] = _pt(39.0 + shift, 85.0)
    extra["gonion_r"] = _pt(-39.0, 85.0)
    return ClassificationInput(
        tier1=Tier1Landmarks(
            nasion=_pt(0.0, 0.0),
            menton=_pt(0.0, 120.0),
            zygion_l=_pt(50.0, 55.0),
            zygion_r=_pt(-50.0, 55.0),
            gonion_l=_pt(39.0 + shift, 85.0),
            gonion_r=_pt(-39.0, 85.0),
            frontotemporale_l=_pt(39.0, 18.0),
            frontotemporale_r=_pt(-39.0, 18.0),
        ),
        extra=extra,
    )


# A mirrored face has an asymmetry index near zero.
def test_mirrored_landmarks_score_near_one():
    result = score_symmetry(prepare_landmarks(_symmetric_sample()))
    assert result.symmetry_score is not None
    assert result.symmetry_score > 0.98
    assert result.asymmetry_index is not None
    assert result.asymmetry_index < 0.2


# An 18-pixel gonion shift must lower the score and show up on that pair.
def test_planted_jaw_offset_lowers_symmetry():
    even = score_symmetry(prepare_landmarks(_symmetric_sample()))
    shifted = score_symmetry(prepare_landmarks(_symmetric_sample(shift=18.0)))
    assert shifted.symmetry_score is not None
    assert even.symmetry_score is not None
    assert shifted.symmetry_score < even.symmetry_score
    gonion = next(item for item in shifted.per_pair_deviations if item.name == "gonion")
    assert gonion.deviation > 10.0


# Yaw of 8 degrees is past the 5-degree limit. The score is still returned.
def test_large_yaw_is_flagged():
    result = score_symmetry(prepare_landmarks(_symmetric_sample()), yaw=8.0)
    assert "symmetry_pose_limited" in result.notes
    assert result.symmetry_score is not None
