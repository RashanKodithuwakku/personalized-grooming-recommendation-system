from fastapi.testclient import TestClient

from face_shape.api import create_app


def _landmarks() -> dict[str, dict[str, float]]:
    return {
        "nasion": {"x": 0.0, "y": 0.0},
        "menton": {"x": 0.0, "y": 87.0},
        "zygion_left": {"x": -50.0, "y": 40.0},
        "zygion_right": {"x": 50.0, "y": 40.0},
        "gonion_left": {"x": -39.0, "y": 70.0},
        "gonion_right": {"x": 39.0, "y": 70.0},
        "frontotemporale_left": {"x": -39.0, "y": 15.0},
        "frontotemporale_right": {"x": 39.0, "y": 15.0},
    }


def test_endpoint_identifies_an_oval_face_and_passes_component1_fields():
    client = TestClient(create_app())
    response = client.post(
        "/api/component-2/face-shape",
        json={
            "landmarks": _landmarks(),
            "jaw_type": {"label": "rounded", "confidence": 0.4},
            "hairline": {"curve": "straight"},
            "jawline": {"label": "rounded"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["face_type"] == "oval"
    assert set(body["face_type_confidence"]) == {
        "oval",
        "round",
        "square",
        "oblong",
        "heart",
        "diamond",
    }
    assert body["ratios"]["mfi"] == 87.0
    assert body["ratios"]["tfi"] is None
    assert body["hairline"] == {"curve": "straight"}
    assert body["jawline"] == {"label": "rounded"}
    assert "symmetry_score" not in body
    assert "balance_score" not in body


def test_endpoint_accepts_depth_on_landmarks():
    client = TestClient(create_app())
    landmarks = {name: {**point, "z": -0.4} for name, point in _landmarks().items()}
    response = client.post("/api/component-2/face-shape", json={"landmarks": landmarks})

    assert response.status_code == 200
    assert response.json()["face_type"] == "oval"


def test_endpoint_rejects_a_missing_core_landmark():
    client = TestClient(create_app())
    landmarks = _landmarks()
    del landmarks["menton"]
    response = client.post("/api/component-2/face-shape", json={"landmarks": landmarks})

    assert response.status_code == 422
