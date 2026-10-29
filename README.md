# GroomAI — Personalized Grooming Recommendation System

GroomAI is a team project for turning facial-analysis data into explainable grooming guidance. The project is organised as independently developed components that exchange structured JSON rather than treating a cosmetic recommendation as a medical or biometric diagnosis.

## Current component map

| Component | Responsibility | Status in this checkout |
| --- | --- | --- |
| Component 1 — capture and profiling | Image-quality checks, landmark extraction, hairline and jawline observations | Contract consumed by Component 2; implementation is on the `Eshara` branch. |
| Component 2 — facial analysis | Face-shape classification plus symmetry and facial-balance scoring | Present in `backend/grooming_component_2_face_shape`. |
| Flutter result client | Uploads a Component 1 landmark JSON file and presents the Component 2 profile | Present in the sibling `../groom_app` directory. |
| Component 3 — recommendations | Ranks catalogue hair, beard, and grooming styles from a structured profile | Separate implementation on the `Nimesha` branch; not wired into this checkout yet. |
| Component 4 — visual preview | Template-based hairstyle/appearance preview research | Early prototype on the `Sayuri` branch; not integrated yet. |

The branches are intentionally documented as separate work. Running this checkout starts Component 2 only; it does not automatically start the Component 1, 3, or 4 services.

## Repository layout

```text
groom_AI/
├── backend/
│   └── grooming_component_2_face_shape/  # FastAPI Component 2 service
├── README.md                              # this overview
└── ../groom_app/                          # Flutter Component 2 client
```

Supporting presentation, research, and sample-material files live outside `groom_AI/` in the workspace root. They are not required to install or run the source code.

## Run the implemented Component 2 flow

1. Start the Python service:

   ```powershell
   cd backend/grooming_component_2_face_shape
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m uvicorn face_shape.api:app --host 0.0.0.0 --port 8000 --reload
   ```

2. In another terminal, start the Flutter client:

   ```powershell
   cd ..\..\groom_app
   flutter pub get
   flutter run
   ```

3. In the app, choose a Component 1 landmark JSON file (for example, the backend test fixture). Confirm or change the service address, then run the reading.

The API documentation is available at `http://127.0.0.1:8000/docs`; the health check is `GET /health`.

## Data flow

```text
Component 1 landmark JSON
        │
        ▼
Component 2: POST /v1/profile
        │  face shape + symmetry + balance
        ▼
Flutter result screens
        │
        └── future: Component 3 recommendation request
                    └── future: Component 4 visual preview
```

`POST /v1/profile` accepts the Component 1 contract: image dimensions, capture quality, pose, named landmarks, and a jawline observation. It returns `ok`, `limited_analysis`, or `error`. A limited result means an optional measurement or pose reduced the available analysis; it is not silently replaced with a fabricated score.

## Development and verification

```powershell
cd backend/grooming_component_2_face_shape
pytest -q
```

The backend requires Python 3.11 or newer. The Flutter client requires the Flutter SDK compatible with the Dart SDK declared in `../groom_app/pubspec.yaml`.

## Branch references

- `Eshara`: Component 1 Flutter/FastAPI facial profiling implementation.
- `Rashan`: Component 2 face-shape analysis (this checkout).
- `Nimesha`: Component 3 gender-aware CatBoost recommendation and ranking service.
- `Sayuri`: Component 4 visual-preview prototype and hairstyle template assets.

## Scope note

GroomAI provides style-oriented, experimental guidance. It is not a medical, dermatological, or identity-verification system. Model and rule scores should be shown as system outputs, not as objective measures of attractiveness or suitability.
