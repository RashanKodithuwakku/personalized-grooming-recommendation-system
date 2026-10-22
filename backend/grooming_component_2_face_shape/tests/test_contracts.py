"""Contract checks: names, aliases, xy pairs, and a complete confidence vector."""

import pytest
from pydantic import ValidationError

from face_shape.contracts import (
    CORE_LANDMARKS,
    FACE_SHAPES,
    MEDIAPIPE_FACE_MESH_INDEX,
    REQUIRED_LANDMARKS,
    FaceShapeResult,
    LandmarkPoint,
    RatioFeatures,
    parse_named_landmarks,
)


# Minimal x/y landmark dict used by the parser tests.
def _point(x: float, y: float) -> dict[str, float]:
    return {"x": x, "y": y}


# One distinct point per core landmark so a swapped name fails the assert.
def _core_payload() -> dict[str, object]:
    return {name: _point(float(index), float(index) + 0.5) for index, name in enumerate(CORE_LANDMARKS)}


# Every core name has a Face Mesh index. Trichion is not in that table.
def test_core_landmark_table_matches_mediapipe_indices():
    for name in CORE_LANDMARKS:
        assert name in MEDIAPIPE_FACE_MESH_INDEX
    assert "trichion" not in MEDIAPIPE_FACE_MESH_INDEX
    assert REQUIRED_LANDMARKS == CORE_LANDMARKS[:6]


# Six core points are enough. Trichion and jaw type stay empty.
def test_parse_accepts_core_points_without_tier2():
    parsed = parse_named_landmarks(_core_payload())

    assert parsed.tier2.trichion is None
    assert parsed.jaw_type is None
    assert parsed.tier1.nasion.x == 0.0
    assert parsed.tier1.zygion_l.x == 2.0


# zygion_left is rewritten to zygion_l before validation.
def test_parse_accepts_left_right_aliases():
    payload = {
        "nasion": _point(0.0, 0.0),
        "menton": _point(0.0, 10.0),
        "zygion_left": _point(-5.0, 4.0),
        "zygion_right": _point(5.0, 4.0),
        "gonion_left": _point(-4.0, 8.0),
        "gonion_right": _point(4.0, 8.0),
        "frontotemporale_left": _point(-4.0, 1.0),
        "frontotemporale_right": _point(4.0, 1.0),
    }
    parsed = parse_named_landmarks(payload)
    assert parsed.tier1.zygion_l.x == -5.0
    assert parsed.tier1.gonion_r.x == 4.0


# Component 1 sends xy rather than separate x and y fields.
def test_parse_accepts_component1_xy_payload():
    payload = {
        name: {"xy": [float(index), float(index) + 0.5], "visible": True, "confidence": 0.9}
        for index, name in enumerate(REQUIRED_LANDMARKS)
    }
    parsed = parse_named_landmarks(payload)
    assert parsed.tier1.menton.y == 1.5
    assert parsed.tier1.frontotemporale_l is None


# Optional tier-2 fields land on tier2 and jaw_type, not in extra.
def test_parse_accepts_trichion_and_jaw_type():
    payload = _core_payload()
    payload["trichion"] = _point(4.0, 1.0)
    payload["jaw_type"] = {"label": "angular", "confidence": 0.82}

    parsed = parse_named_landmarks(payload)

    assert parsed.tier2.trichion is not None
    assert parsed.tier2.trichion.y == 1.0
    assert parsed.jaw_type is not None
    assert parsed.jaw_type.label == "angular"


# A missing gonion names the landmark in the error.
def test_parse_rejects_missing_core_landmark():
    payload = _core_payload()
    del payload["gonion_r"]

    with pytest.raises(ValueError, match="gonion_r"):
        parse_named_landmarks(payload)


# NaN is not a usable coordinate.
def test_landmark_rejects_non_finite_coordinate():
    with pytest.raises(ValidationError):
        LandmarkPoint.model_validate({"x": float("nan"), "y": 1.0})


# Dropping diamond from the six-class vector is invalid.
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
