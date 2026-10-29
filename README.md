# GroomAI — Personalized Grooming Recommendation System

GroomAI is a collaborative, AI-assisted grooming project for facial analysis, style ranking, and visual-preview research. Its components communicate through structured data contracts so each part can be developed and tested independently.

## Project components

| Component | Purpose | Branch |
| --- | --- | --- |
| Component 1 — facial profiling | Photo-quality checks, facial landmarks, hairline, and jawline observations | `Eshara` |
| Component 2 — face-shape analysis | Face-shape classification, symmetry, and facial-balance scoring | `Rashan` |
| Component 3 — recommendation engine | CatBoost-based ranking of hair, beard, and grooming catalogue styles | `Nimesha` |
| Component 4 — visual preview | Template-based hairstyle/appearance preview prototype | `Sayuri` |

## Getting started

The components are currently maintained on their respective branches. Check out the branch you need before running it:

```bash
git fetch origin
git switch Rashan    # Component 2 face-shape API
```

For the implemented Component 2 flow, start the FastAPI service in `backend/grooming_component_2_face_shape`, then run the companion Flutter client from the local `groom_app` workspace directory. The Component 2 branch README and its backend README contain the exact setup, API, and test commands.

## Integration direction

```text
Component 1 landmark/profile JSON
        │
        ▼
Component 2 face-shape, symmetry, and balance analysis
        │
        ▼
Component 3 ranked style recommendations
        │
        ▼
Component 4 visual preview
```

This diagram describes the intended integration direction; the components are not all merged or deployed as one service yet.

## Scope

GroomAI provides experimental, style-oriented guidance. It is not a medical, dermatological, or identity-verification system. Scores and recommendations are system outputs and should not be represented as objective measures of appearance or suitability.
