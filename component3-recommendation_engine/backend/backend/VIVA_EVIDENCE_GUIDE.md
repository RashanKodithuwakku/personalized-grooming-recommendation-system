# Component 3 — Concise viva evidence guide

Use this sheet to walk **dataset → training cells → evaluation → saved models → API**, with exact paths and honest research limits.

---

## 1. End-to-end flow (repository paths)

```text
Facial attributes (manual JSON today; Component 2 later)
        │
        ▼
backend/app/schemas/requests.py          validate profile + optional confidence
        │
        ▼
backend/app/services/eligibility.py      catalogue filters / beard coverage
        │
        ├─► backend/models/models/*_ranker_gender_aware.cbm
        ├─► backend/models/models/compatibility_scorer_gender_aware.cbm
        └─► backend/datasets/rating_parameters.json   (weighted rules)
        │
        ▼
backend/app/services/recommendation_engine.py
   hybrid: 0.50 predicted_compat + 0.30 rank_percentile + 0.20 rule
   optional ranking_mode=confidence_aware → adjust RULE term only
        │
        ▼
POST /api/v1/recommendations
```

| Stage | Exact path |
|-------|------------|
| Profiles / pairs / catalogue | `backend/datasets/generated_data/` (`profiles.csv`, `training_pairs.csv`, `style_catalogue.csv`, `splits/`) |
| Dataset metadata | `backend/datasets/dataset_metadata.json` |
| Rule parameters | `backend/datasets/rating_parameters.json` |
| Runtime schema | `backend/models/gender_aware_schema.json` |
| Dataset schema copy | `backend/datasets/gender_aware_schema.json` |
| Training notebook | `backend/training/notebooks/Component3_Training_Executed.ipynb` |
| Notebook guide | `backend/training/README.md` |
| Model binaries | `backend/models/models/*.cbm` |
| Run hashes | `backend/models/run_information.json` |
| Evaluation | `backend/models/gender_evaluation.csv`, `gender_scorer_errors.csv` |
| Test predictions | `backend/models/gender_test_predictions.csv` |
| API | `backend/app/` |
| Postman | `backend/postman/Component3.postman_collection.json` |
| TAF (original form) | `backend/docs/requirements/TAF-J26-IT-403 (version 3) (1) (3).pdf` |
| Full audit | `backend/COMPONENT3_BACKEND_AUDIT.md` |

---

## 2. Duplicate schemas (do not delete either)

| File | Role |
|------|------|
| `backend/models/gender_aware_schema.json` | **Runtime** (`SCHEMA_PATH` / `paths.DEFAULT_SCHEMA_PATH`) |
| `backend/datasets/gender_aware_schema.json` | Dataset package copy / evidence |

**Similar:** `profile_features`, `model_features`, `categorical_features`, categories, gender values, `female_beard_rows_removed`, `rating_column`, `ranking_group`, `rating_source`, `profile_source` — **identical**.

**Difference:** models copy adds only:

- `gender_feature_used`: true  
- `confidence_calibrated`: false  

**Meaningful incompatibility for inference?** **No.** Feature contracts match; CatBoost feature order agrees with both lists.

---

## 3. Training cells → evaluation → models

See `backend/training/README.md` for numbering details.

| 0-based index | What to show |
|---------------|--------------|
| 95 | Final GenderAware training + export |
| 96 | Evaluation outputs matching CSVs |
| 97 | Download zip = `run_information.json` run id |

Earlier CLIP error (index **57**) is historical and does **not** define the shipped models.

---

## 4. Metric definitions and **actual** values

Source CSV: `backend/models/gender_evaluation.csv` (and `gender_scorer_errors.csv`).

| Metric | Meaning |
|--------|---------|
| Ranker **top-choice agreement** | Fraction of test profiles where the style with the highest **ranker score** matches the style with the highest **rule-generated** rating (within category). **Not** classification accuracy of “human preferred style.” |
| Ranker **NDCG@3** | Ranking quality of the top-3 ordered by ranker score vs relevance derived from rule-generated ratings. |
| Scorer **MAE** / **RMSE** | Error of compatibility regressor vs rule-generated `rating` on the 1–5 scale. |

### Actual metrics (from current CSV)

| Category | Gender | Top-choice agreement | NDCG@3 | MAE | RMSE |
|----------|--------|----------------------|--------|-----|------|
| hair | male | 0.9557 | 0.9999 | 0.0175 | 0.0217 |
| hair | female | 0.9577 | 0.9998 | 0.0168 | 0.0211 |
| beard | male | 0.9667 | 0.9998 | 0.0252 | 0.0330 |
| grooming | male | 0.9601 | 0.9999 | 0.0173 | 0.0220 |
| grooming | female | 0.9599 | 0.9999 | 0.0183 | 0.0232 |

**Generated-label agreement ≠ human suitability accuracy.**  
`dataset_metadata.json`: `rating_source=rule_generated`, `human_reviewed=false`, `expert_validated=false`.

---

## 5. Postman requests to demonstrate

Collection: 68 requests (see `coverage_matrix.md`, `verification_report.md`).

| Demo | Folder / request IDs |
|------|----------------------|
| Inference / happy path | `03.01` male all categories; `03.02` female |
| Weighted rules + hybrid 0.50/0.30/0.20 | `05.01`–`05.03` |
| Confidence input-quality flagging | `06.01`–`06.08` |
| Confidence-aware **ranking** (rule term only) | `09.01`–`09.07` |
| Eligibility (female beard, exclusions, facial hair) | `04.01`–`04.08` |
| Invalid input (422) | `07.*` |

Current Newman evidence: **68** requests, **404** assertions, **0** failed  
(`verification_report.md`; collection SHA256 `9d5ae2a4ab5394562a56beb758c1c4b5adc6242b7a2f85f55cf13308ba776ded`).

---

## 6. Ranking modes (say this clearly)

### Standard (`hybrid_model_rank_rules_v1`)

```text
hybrid = 0.50 * normalized_predicted_compatibility
       + 0.30 * rank_percentile
       + 0.20 * original rule_compatibility_score
```

### Confidence-aware (`hybrid_confidence_adjusted_rules_v1`)

- Requires all **nine** facial confidence values (gender optional; excluded from facial weighting).
- `A = sum(w_i * c_i)`, `S_j = sum(w_i * c_i * s_ij)`, adjusted = `S_j / A` if `A > 0`.
- **Only the rule hybrid term** uses the adjusted score. CatBoost still consumes profile values (no ML uncertainty propagation).
- `recommendation_support_score` (`S_j`) is a **heuristic** confidence-weighted rule-support score — **not** a calibrated probability.
- `recommendation_confidence` remains **`null` / `not_calibrated`**.
- All-zero confidence → documented **fallback** to standard ranking + `review_required`.

---

## 7. TAF Component 3 bullets (source document)

**File:** `backend/docs/requirements/TAF-J26-IT-403 (version 3) (1) (3).pdf`  
**Member:** Nimesha A.W.P.T. (IT23270992) — **Page 9**  
**Layer context:** Personalized Style Recommendation — **Page 5**

| TAF task (p. 9) | Backend evidence | Gap |
|-----------------|------------------|-----|
| Use structured facial profile from C2; match hairstyle/beard/grooming | Manual JSON contract + catalogue; C2 not wired | Upstream integration open |
| Hybrid rule-based filtering + weighted compatibility | Eligibility + `rating_parameters.json` + hybrid mix | — |
| Confidence-aware Top-N on face shape, proportions, jawline, forehead, hairline, symmetry | Flagging + optional `ranking_mode=confidence_aware` | TAF wording “confidence scores” — **calibrated** confidence **not** delivered (`null`) |
| Separate hair / beard / facial grooming recommendations | Categories hair/beard/grooming | Grooming catalogue = eyebrow styles |
| Novelty: Top-N with confidence scores + explainable matching | Top-N + explanations + heuristic support/quality | Calibrated confidence unfinished; human validation unfinished |

---

## 8. What is complete vs not

| Layer | Status |
|-------|--------|
| Agreed / implemented FastAPI backend engineering | Complete (see audit) |
| Original TAF wording fully closed (esp. calibrated confidence) | **Partial** |
| Component 2 / image pipeline integration | **Not done** |
| Frontend (Component 4 presentation) | **Out of this backend scope** |
| Human suitability validation | **Not done** |
| Calibrated recommendation confidence | **Not done** |
