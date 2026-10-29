# Component 2 — Face-Shape Analysis API

FastAPI service for GroomAI’s Component 2. It consumes the landmark payload produced by Component 1 and returns a structured facial profile for the Flutter client and a future recommendation engine.

## What it calculates

- Classification among `oval`, `round`, `square`, `oblong`, `heart`, and `diamond`.
- Morphological face class and anthropometric ratio features.
- Left/right symmetry and vertical/horizontal facial-balance scores.
- A grooming-suitability index composed of shape certainty (50%), symmetry (25%), and balance (25%).
- Processing notes and an explicit `limited_analysis` status when pose or optional landmark data limits the reading.

The service does not accept images or run landmark detection. Component 1 must provide named landmarks, image dimensions, quality, pose, jawline, and optional hairline observations.

## Requirements

- Python 3.11+
- FastAPI, Uvicorn, and Pydantic (listed in `requirements.txt`)

## Install and run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn face_shape.api:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://127.0.0.1:8000/docs` for interactive OpenAPI documentation.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Service metadata and route list. |
| `GET` | `/health` | Liveness response. |
| `POST` | `/v1/profile` | Full Component 1 payload → facial profile, symmetry, balance, and suitability. |
| `POST` | `/api/component-2/face-shape` | Slim named-landmark payload → face-shape result only. |

## Full-profile request

Use the fixture as a tested request example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/profile `
  -H "Content-Type: application/json" `
  --data-binary "@tests/fixtures/component1_payload_example.json"
```

The full request requires `request_id`, `image`, `quality`, `pose`, `landmarks`, and `jawline`. See `face_shape/payload.py` for the Pydantic contract.

## Response semantics

`POST /v1/profile` returns:

- `status`: `ok`, `limited_analysis`, or `error`.
- `face_shape_label` and `face_shape_confidence` where available.
- Symmetry, balance, and suitability fields when the necessary measurements are valid.
- `processing_notes` explaining limitations instead of inventing measurements.

Schema errors return HTTP 422. Unexpected failures return a JSON HTTP 500 response, and the traceback remains in the server log.

## Test

```powershell
pytest -q
```

The test suite covers geometry, thresholds, scoring, payload contracts, pipeline behaviour, and HTTP endpoints.

## Client integration

The sibling Flutter client at `../../../groom_app` posts the Component 1 JSON directly to `/v1/profile`. Default local addresses are `127.0.0.1:8000` for desktop/web and `10.0.2.2:8000` for an Android emulator. CORS permits local `localhost`, `127.0.0.1`, and Android-emulator origins.

## Scope

This component produces experimental, style-oriented measurements. It is not a clinical or identity-verification service.
