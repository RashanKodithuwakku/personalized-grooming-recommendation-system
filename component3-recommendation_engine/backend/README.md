# Component 3 — Style Recommendation and Ranking Engine

Python FastAPI backend that ranks hair, beard, and grooming styles from structured facial attributes using the existing gender-aware CatBoost models.

This component does **not** perform image analysis, face detection, or model training. It accepts JSON facial attributes now; a future Component 2 service should populate the same request contract.

## What this API does

1. Validates a facial profile against the gender-aware training contract.
2. Selects eligible catalogue styles (eligibility / model-coverage rules).
3. Builds features in the exact CatBoost feature order.
4. Runs the category CatBoost ranker and the shared compatibility regressor.
5. Applies a provisional hybrid ordering policy.
6. Returns ranked styles with transparent score fields and explanations.

## Artifact layout (do not flatten)

```text
backend/
  datasets/
    generated_data/style_catalogue.csv
    gender_aware_schema.json
    dataset_metadata.json
  models/
    models/                         # nested binaries are intentional
      hair_ranker_gender_aware.cbm
      beard_ranker_gender_aware.cbm
      grooming_ranker_gender_aware.cbm
      compatibility_scorer_gender_aware.cbm
    gender_aware_schema.json
    run_information.json
    gender_evaluation.csv
    gender_test_predictions.csv
  app/
  tests/
```

## Installation

### Windows (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

### Linux / macOS

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

CatBoost **1.2.10** matches the training package recorded in `models/run_information.json`.

## Run the API

From `backend/`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json
- Liveness: `GET /health/live`
- Readiness: `GET /health/ready`

## Example recommendation request

Windows PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/recommendations `
  -H "Content-Type: application/json" `
  --data-binary "@examples/recommendation_request_male.json"
```

Linux / macOS:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  --data-binary @examples/recommendation_request_female.json
```

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Artifact / model readiness |
| GET | `/api/v1/capabilities` | Categories, coverage limits, rule status |
| GET | `/api/v1/input-schema` | Request contract and supported values |
| GET | `/api/v1/styles` | Catalogue (`?category=hair\|beard\|grooming`) |
| GET | `/api/v1/models/info` | Model hashes and evaluation summary |
| POST | `/api/v1/recommendations` | Hybrid recommendations |

## Flutter / future client notes

- Call `POST /api/v1/recommendations` with JSON body matching `/api/v1/input-schema`.
- Configure CORS via `CORS_ORIGINS` (comma-separated allowlist). Credentialed wildcard CORS is rejected.
- Send optional `X-Request-ID` for correlation; it is echoed back when provided.
- Do not treat `compatibility_score` or ranker scores as confidence.
- `recommendation_confidence` is always `null` with status `not_calibrated`.

## Component 2 integration

Component 2 (image analysis) should later populate the same `profile` object:

- numeric: `face_length_ratio`, `jaw_width_ratio`, `upper_width_ratio`, `lower_face_ratio`, `symmetry`
- categorical: `face_shape`, `jawline`, `forehead`, `hairline`, `gender`
- optional: `attribute_confidence` map with values in `[0, 1]`

Operational preferences (`include_beard`, `facial_hair_available`, `excluded_style_ids`) stay outside model features.

## Inference flow

```text
JSON profile
  -> validate / normalize (case, whitespace only)
  -> OOD warnings from empirical training ranges
  -> per requested category:
       catalogue candidates
       -> eligibility rules
       -> feature matrix (exact model order)
       -> category CatBoostRanker
       -> shared CatBoostRegressor (compatibility)
       -> optional weighted rules (if configured)
       -> provisional hybrid ordering
  -> response with raw + display scores and explanations
```

### Score fields

| Field | Meaning |
|-------|---------|
| `raw_ranker_score` | Category ranker output (not a probability; not comparable across categories) |
| `raw_predicted_compatibility_rating` | Shared scorer prediction on ~1–5 rating scale |
| `display_compatibility_rating` | Clipped to `[1, 5]` |
| `compatibility_score` | `100 * (clipped_rating - 1) / 4` — **rescaled predicted rating**, not accuracy or confidence |

Training ratings were **rule-generated**, not human-reviewed. Evaluation metrics measure agreement with those generated ratings, not real-world human suitability.

## Eligibility rules (application defaults / model coverage)

- Female profile without explicit `include_beard=true` → skip beard.
- Any profile with `include_beard=false` → skip beard.
- Male profile with no explicit beard preference → beard may be included.
- Female + explicit `include_beard=true` → `unsupported_model_coverage` for beard (trained on male only); other categories continue.
- `facial_hair_available=false` excludes only catalogue styles with `requires_facial_hair=true` (clean-shaven remains eligible).
- `excluded_style_ids` are never reintroduced to fill `top_n`.
- Hair / grooming have no invented gender bans; catalogue `gender_restriction` is respected when present.

## Ranking weights (provisional)

Active policy when rule categories are parity-verified (default with recovered parameters):

- `0.50 * normalized predicted compatibility + 0.30 * within-category rank percentile + 0.20 * rule compatibility`

Fallback when rules are missing/unverified for a category:

- `0.70 * normalized predicted compatibility + 0.30 * within-category rank percentile`

These hybrid mix weights are **provisional engineering defaults**, not learned or research-validated weights, and not the original training formula. Tie-aware rank percentiles are used; `style_id` is the final deterministic tie-breaker. A single eligible candidate receives percentile `1.0`.

## Weighted compatibility rules

Recovered original parameters live at `datasets/rating_parameters.json`
(from `Component3_AllCategories_20261008T121138_253749Z.zip`). The file is
loaded by default via `RULE_PARAMETERS_PATH` and is not modified by the API.

Coverage: H001–H008, B001–B004, G001–G004 with per-category weight vectors.

Established similarity calculation (verified against `training_pairs.rating`):

1. Ratio terms + symmetry: Gaussian  
   `exp(-0.5 * ((value - target) / scale)^2)`
2. Categorical terms: `categorical_match_score` (1.0) or `categorical_nonmatch_score` (0.35)
3. `weighted_compatibility = sum(weight_i * similarity_i)` using the category weight vector
4. Dataset labels: `round(1 + 4 * weighted_compatibility, 4)`

Parity tolerance is `1e-4`, justified by the stored 4-decimal rating precision.

`parameter_status` remains `provisional_unvalidated`. Dataset-label parity does
**not** mean human expert validation. Recommendation confidence stays
`not_calibrated`.

## Catalogue coverage (practical)

Current catalogue (verified from `style_catalogue.csv`):

- **8** hairstyle candidates (H001–H008)
- **4** beard candidates (B001–B004)
- **4** grooming candidates (G001–G004), focused on **eyebrow styling**

Recommendations do **not** evaluate hair length, hair texture, hair density, or
maintenance preferences. Those inputs are unsupported. Hair styles are not
arbitrarily restricted by gender under the current catalogue.

## Ranking modes

| `ranking_mode` | Default | Behavior |
|----------------|---------|----------|
| `standard` | yes | Existing hybrid (`hybrid_model_rank_rules_v1`). Confidence is for input-quality flagging only and does **not** reorder candidates. |
| `confidence_aware` | no | Optional. Requires all nine facial confidence values. Policy `hybrid_confidence_adjusted_rules_v1` replaces **only** the rule hybrid term with `confidence_adjusted_rule_score = S_j / A`. |

`confidence_source` (`manual` | `upstream` | `unspecified`) is **provenance only** and does not change scores. Use `manual` for demo/test until upstream components populate the same `attribute_confidence` contract. Confidence values are never fabricated.

Confidence-aware formulas (original weights `w_i`, similarities `s_ij`, confidence `c_i`):

- `A = rule_confidence_coverage = sum(w_i * c_i)`
- `S_j = recommendation_support_score = sum(w_i * c_i * s_ij)`
- `confidence_adjusted_rule_score = S_j / A` when `A > 0`, else `null`

When all confidences are zero (`A = 0`): no divide-by-zero; **fallback** to standard ranking; `review_required`; support `0`; adjusted score `null`.

CatBoost models still consume supplied profile values; this mode does **not** propagate uncertainty through the ML models. Uniform nonzero scaling of all confidences preserves the adjusted rule score but changes support and quality. Not every confidence change must change the top style.

## Confidence-aware Top-N flagging (heuristic)

Policy name: `confidence_aware_topn_flagging_v1` (active in both ranking modes for quality/disposition).

In `ranking_mode=standard` this is **confidence-aware flagging of Top-N results using an input-quality
heuristic**. It does **not** reorder candidates, does **not** multiply hybrid
scores by profile quality, and is **not** calibrated recommendation confidence.

Facial confidence aggregate uses the nine weighted-rule attributes:

`face_length_ratio`, `jaw_width_ratio`, `upper_width_ratio`, `lower_face_ratio`,
`symmetry`, `face_shape`, `jawline`, `forehead`, `hairline`

Gender confidence may still be accepted for API compatibility but is **excluded**
from that nine-attribute aggregate.

| Field | Meaning |
|-------|---------|
| `confidence_attributes_provided` / `confidence_attributes_missing` | Upstream confidence presence for facial attributes |
| `confidence_coverage` | observed / 9 |
| `input_quality_score` | Heuristic reliability (global: equal-weight mean of supplied facial confidences; category: rule-weighted mean of supplied) |
| `assessment` | `unknown` → `insufficient_coverage` → `low` → `adequate` |
| `recommendation_disposition` | `standard` or `review_required` |
| `recommendation_confidence` | Always `null` / `not_calibrated` |

Deprecated aliases (exact same values as the canonical confidence_* fields):

- `attributes_provided` → `confidence_attributes_provided`
- `attributes_missing` → `confidence_attributes_missing`
- `coverage` → `confidence_coverage`

These aliases refer to **missing confidence values**, not missing facial
measurements. Missing required profile values remain request-validation errors.

If confidence is omitted: recommendations are still returned (manual-input demos),
`input_quality_score=null`, `confidence_coverage=0`, `assessment=unknown`,
`caution_flag=true` with reason `confidence_not_provided`, and category
disposition `review_required`.

## Score terminology

- `compatibility_score`: rescaled predicted rating (original model compatibility)
- `rule_compatibility_score`: original weighted rule agreement
- `confidence_adjusted_rule_score`: confidence-adjusted rule compatibility (`S_j/A`)
- `recommendation_support_score`: heuristic confidence-weighted rule support (`S_j`), not a probability
- `rule_confidence_coverage`: `A = sum(w_i * c_i)`
- `hybrid_score`: final ranking / ordering score
- `input_quality_score`: heuristic input reliability
- `recommendation_confidence`: unavailable until calibrated (`null` / `not_calibrated`)

Human suitability validation and calibrated recommendation confidence remain
**unfinished research work**. Passing API tests does not validate the full research.

## Tests

From `backend/`:

```bash
pytest -q
```

Real-model integration tests load the local `.cbm` binaries and compare a small sample against `models/gender_test_predictions.csv` using absolute tolerance `1e-5`. Mocked predictors are not treated as proof of inference.

## Docker (optional)

From `backend/` (copies local `models/` and `datasets/` into the image):

```bash
docker build -t style-ranker-c3 .
docker run --rm -p 8000:8000 style-ranker-c3
```

## Important research caveats

- Generated-data evaluation is not human suitability validation.
- Adding gender as a model feature does not by itself prove gender-specific suitability.
- Full research validation is not claimed complete.
- This service does not persist submitted profiles or recommendations.
