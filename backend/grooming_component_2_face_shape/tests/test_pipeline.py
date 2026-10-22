"""End-to-end profile on the checked-in Component 1 example.

The fixture is a mesoprosopic oval. The response must include the
suitability index and must not include a proportion score.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import approx

from face_shape.api import create_app
from face_shape.payload import Component1Payload
from face_shape.pipeline import analyse_profile


FIXTURE = Path(__file__).parent / "fixtures" / "component1_payload_example.json"


# Load the sample Component 1 JSON used as the pipeline fixture.
def _example() -> Component1Payload:
    return Component1Payload.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


# Shape class, everyday label, and the 0.50/0.25/0.25 composite.
def test_example_payload_is_mesoprosopic_oval():
    profile = analyse_profile(_example())
    assert profile.status in {"ok", "limited_analysis"}
    assert profile.face_shape_class == "Mesoprosopic"
    assert profile.face_shape_label == "oval"
    assert profile.mfi_value is not None
    assert 85.0 <= profile.mfi_value < 90.0
    assert profile.anthropometric_ratios is not None
    assert profile.anthropometric_ratios.jmi == approx(77.6, abs=1.5)
    assert profile.anthropometric_ratios.fzi == approx(77.1, abs=1.5)
    assert profile.symmetry_score is not None
    assert profile.balance_score is not None
    assert profile.shape_score == max(profile.face_shape_confidence.values())
    expected = (
        0.50 * profile.shape_score
        + 0.25 * profile.symmetry_score
        + 0.25 * profile.balance_score
    )
    assert profile.compatibility_score == approx(expected)
    assert profile.grooming_suitability_index == approx(round(100.0 * expected, 1))
    assert profile.score_weights == {"shape": 0.50, "symmetry": 0.25, "balance": 0.25}
    dumped = profile.model_dump()
    assert "proportion_score" not in dumped


# POST /v1/profile is the payload the frontend result screen reads.
def test_profile_endpoint_returns_display_scores():
    client = TestClient(create_app())
    response = client.post("/v1/profile", json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert response.status_code == 200
    body = response.json()
    assert body["face_shape_label"] == "oval"
    assert body["face_shape_class"] == "Mesoprosopic"
    assert "symmetry_score" in body
    assert "balance_score" in body
    assert "shape_score" in body
    assert "compatibility_score" in body
    assert "grooming_suitability_index" in body
    assert "proportion_score" not in body
    assert body["score_weights"] == {"shape": 0.50, "symmetry": 0.25, "balance": 0.25}
    assert client.get("/health").json()["status"] == "ok"


# A capture Component 1 already rejected does not receive a face label.
def test_rejected_payload_returns_error_status():
    payload = _example()
    payload.quality.status = "rejected"
    profile = analyse_profile(payload)
    assert profile.status == "error"
