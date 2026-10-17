import pytest
from pydantic import ValidationError

from face_shape.contracts import (
    CORE_LANDMARKS,
    FACE_SHAPES,
    MEDIAPIPE_FACE_MESH_INDEX,
    FaceShapeResult,
    LandmarkPoint,
    RatioFeatures,
    parse_named_landmarks,
)


def _point(x: float, y: float) -> dict[str, float]:
    return {"x": x, "y": y}


def _core_payload() -> dict[str, object]:
    return {name: _point(float(index), float(index) + 0.5) for index, name in enumerate(CORE_LANDMARKS)}


def test_core_landmark_table_matches_mediapipe_indices():
    assert tuple(MEDIAPIPE_FACE_MESH_INDEX) == CORE_LANDMARKS
    assert len(set(MEDIAPIPE_FACE_MESH_INDEX.values())) == 8
    assert "trichion" not in MEDIAPIPE_FACE_MESH_INDEX


def test_parse_accepts_core_points_without_tier2():
    parsed = parse_named_landmarks(_core_payload())

    assert parsed.tier2.trichion is None
    assert parsed.jaw_type is None
    assert parsed.tier1.nasion.x == 0.0


def test_parse_accepts_trichion_and_jaw_type():
    payload = _core_payload()
    payload["trichion"] = _point(4.0, 1.0)
    payload["jaw_type"] = {"label": "angular", "confidence": 0.82}

    parsed = parse_named_landmarks(payload)

    assert parsed.tier2.trichion is not None
    assert parsed.tier2.trichion.y == 1.0
    assert parsed.jaw_type is not None
    assert parsed.jaw_type.label == "angular"


def test_parse_rejects_missing_core_landmark():
    payload = _core_payload()
    del payload["gonion_right"]

    with pytest.raises(ValueError, match="gonion_right"):
        parse_named_landmarks(payload)


def test_landmark_rejects_non_finite_coordinate():
    with pytest.raises(ValidationError):
        LandmarkPoint.model_validate({"x": float("nan"), "y": 1.0})


def test_result_requires_a_full_confidence_vector():
    confidence = {name: 0.0 for name in FACE_SHAPES}
    del confidence["diamond"]

    with pytest.raises(ValidationError, match="diamond"):
        FaceShapeResult.model_validate(
            {
                "face_type": "oval",
                "face_type_confidence": confidence,
                "ratios": RatioFeatures(),
            }
        )
