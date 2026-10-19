import json
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import approx

from face_shape.api import create_app
from face_shape.payload import Component1Payload
from face_shape.pipeline import analyse_profile


FIXTURE = Path(__file__).parent / "fixtures" / "component1_payload_example.json"


def _example() -> Component1Payload:
    return Component1Payload.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


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
    dumped = profile.model_dump()
    assert "compatibility_score" not in dumped
    assert "proportion_score" not in dumped


def test_profile_endpoint_returns_scores_without_composite():
    client = TestClient(create_app())
    response = client.post("/v1/profile", json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert response.status_code == 200
    body = response.json()
    assert body["face_shape_label"] == "oval"
    assert body["face_shape_class"] == "Mesoprosopic"
    assert "symmetry_score" in body
    assert "balance_score" in body
    assert "compatibility_score" not in body
    assert client.get("/health").json()["status"] == "ok"


def test_rejected_payload_returns_error_status():
    payload = _example()
    payload.quality.status = "rejected"
    profile = analyse_profile(payload)
    assert profile.status == "error"
