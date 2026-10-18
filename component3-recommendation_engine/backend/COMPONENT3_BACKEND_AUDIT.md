# Component 3 Backend Audit Report

**Auditor mode:** evidence-based inspection (application/datasets/models unchanged).  
**Repository root inspected:** `backend/` under Softedge / Nimesha Component 3 workspace.  
**Initial audit execution:** 2026-10-13 — isolated `uvicorn` on `http://127.0.0.1:8010`.  
**Evidence refresh:** 2026-10-13 — documentation / Postman / TAF mapping updates (this revision).  
**Temporary audit outputs:** `%TEMP%\c3_backend_audit\` (API scenario JSON + original Newman export source).

---

## 0. Evidence refresh status (post-audit follow-up)

| Issue from initial audit | Resolution | Remaining? |
|--------------------------|------------|------------|
| Stale Postman `58`/`369` vs collection `68` | **Resolved:** old reports archived; `newman-report.json` + `verification_report.md` refreshed from actual Newman run (68 req / 404 asserts / 0 failed; duration 7986 ms; target `:8010`; collection SHA256 `9d5ae2a4…776ded`) | No (for current collection) |
| Notebook cell guidance unclear | **Resolved:** `backend/training/README.md` (0-based vs 1-based; final vs experimental; CLIP note; null `execution_count`) | Notebook still composite history |
| Dual `gender_aware_schema.json` confusion | **Resolved:** documented in `VIVA_EVIDENCE_GUIDE.md` + §2; runtime = `models/` | Keep both files |
| Missing viva walkthrough | **Resolved:** `backend/VIVA_EVIDENCE_GUIDE.md` | — |
| TAF / original requirements unavailable | **Resolved as source found:** `backend/docs/requirements/TAF-J26-IT-403 (version 3) (1) (3).pdf` — Nimesha C3 mapped in §1.2 | Calibrated “confidence scores” / C2 integration / research validation still open |
| Component 2 integration | **Not claimed complete** | Remains open |
| Human suitability / calibrated confidence | **Not claimed complete** | Remains open |

---

## 1. Authoritative requirements

### 1.1 Source documents found in this repository

| Document | Path | Role |
|----------|------|------|
| **TAF (Topic Assessment Form)** | `backend/docs/requirements/TAF-J26-IT-403 (version 3) (1) (3).pdf` | Original project form (11 pages); Nimesha Component 3 on **p. 9** |
| Backend README | `backend/README.md` | Engineering contract for API / ranking modes |
| `.env.example` | `backend/.env.example` | Hybrid weight defaults |
| Dataset / model READMEs | `backend/datasets/README.txt`, `backend/models/README.txt` | Artifact layout |
| Training notebook guide | `backend/training/README.md` | Viva cell map |
| Viva evidence guide | `backend/VIVA_EVIDENCE_GUIDE.md` | Demo path + metrics |
| Postman docs | `backend/postman/README.md`, `coverage_matrix.md`, `verification_report.md` | API verification |

### 1.2 Original TAF — Nimesha Component 3 (verified against PDF)

**Real path:** `backend/docs/requirements/TAF-J26-IT-403 (version 3) (1) (3).pdf`  
**Project:** Personalized Grooming Recommendation System with AI Assistance (J26-IT-403)  
**Member:** Nimesha A.W.P.T., IT23270992 — **Page 9**  
**Pipeline layer:** Personalized Style Recommendation — **Page 5**

| TAF requirement (p. 9 wording) | Status vs backend | Code / evidence | Remaining gap |
|--------------------------------|-------------------|-----------------|---------------|
| Utilize structured facial profile from Component 2; match hairstyle, beard, facial grooming options | **PARTIAL** | Manual JSON profile contract (`schemas/requests.py`); catalogue H/B/G; API ready for upstream fields (`/api/v1/input-schema`) | **Component 2 not integrated** — profile is manual for now |
| Apply hybrid rule-based filtering and weighted compatibility scoring using multiple facial attributes | **VERIFIED** | Eligibility + `rating_parameters.json` (9 facial attrs) + hybrid weights 0.50/0.30/0.20 | Rule params remain `provisional_unvalidated` |
| Rank styles using confidence-aware Top-N based on face shape, proportions, jawline, forehead, hairline, symmetry | **PARTIAL** | Input-quality flagging + optional `ranking_mode=confidence_aware` adjusting **rule term only** | TAF novelty text also asks for **confidence scores**; API keeps `recommendation_confidence=null` / `not_calibrated` |
| Provide separate recommendations for hairstyles, beard styles, and facial grooming styles | **VERIFIED** | Categories `hair` / `beard` / `grooming`; live + Postman | Grooming catalogue is eyebrow-focused (documented) |
| Novelty: Ranked Top-N with confidence scores and explainable style matching | **PARTIAL** | Top-N + explanations + heuristic support/quality fields | **Calibrated confidence scores not implemented**; explanations are pipeline/score-source transparent, not causal human claims |

**Separations (do not conflate):**

| Layer | Status |
|-------|--------|
| Agreed backend engineering completion | Complete (prior audit + this refresh) |
| Original TAF literal “confidence scores” | **Not fully met** (heuristic quality/support only) |
| Upstream C2 integration | **Not done** |
| Frontend / C4 presentation | **Out of backend scope** |
| Human suitability research validation | **Not done** |

### 1.3 Agreed backend scope (engineering — beyond strict TAF wording)

| In scope (agreed backend) | Out of scope / unfinished |
|---------------------------|---------------------------|
| Structured facial-profile JSON (manual for now) | Upstream image analysis / face detection |
| Hair, beard, grooming recommendations | Frontend work |
| Eligibility filtering | Database |
| Weighted compatibility over nine facial attributes | Retraining / changing rule parameters |
| 3 CatBoost rankers + shared compatibility regressor | Human suitability validation |
| Hybrid Top-N + explanations | Calibrated `recommendation_confidence` |
| `standard` + optional `confidence_aware` ranking | Claiming research fully validated by API tests |

---

## 2. File location inventory

Legend: **R** = runtime-required for recommendations; **E** = training/viva evidence; **T** = test/tooling.

| Expected logical path | Present? | Actual relative path | Purpose | Runtime reference | Notes |
|-----------------------|----------|----------------------|---------|-------------------|-------|
| `training/notebooks/Component3_Training_Executed.ipynb` | Yes | `backend/training/notebooks/Component3_Training_Executed.ipynb` | Training/viva evidence | Not loaded at runtime | E |
| `datasets/generated_data/profiles.csv` | Yes | `backend/datasets/generated_data/profiles.csv` | 6,000 profiles | Empirical OOD ranges (train split), evidence | E / partial R |
| `datasets/generated_data/ratings.csv` | Yes | `backend/datasets/generated_data/ratings.csv` | Ratings export | Not required for inference | E |
| `datasets/generated_data/style_catalogue.csv` | Yes | `backend/datasets/generated_data/style_catalogue.csv` | 16-style catalogue | `CATALOGUE_PATH` / `paths.DEFAULT_CATALOGUE_PATH` | R |
| `datasets/generated_data/training_pairs.csv` | Yes | `backend/datasets/generated_data/training_pairs.csv` | 84k pairs; rule parity | Startup parity check | R (parity) / E |
| `datasets/generated_data/splits/*` | Yes | `train.csv`, `validation.csv`, `test.csv` | Profile-level splits | Train split for OOD ranges | E / partial R |
| `datasets/gender_aware_schema.json` | Yes | `backend/datasets/gender_aware_schema.json` | Dataset schema copy | **Not** default `SCHEMA_PATH` | Duplicate of models schema minus 2 keys |
| `datasets/dataset_metadata.json` | Yes | `backend/datasets/dataset_metadata.json` | Dataset metadata | Loaded for notes/info | E / meta |
| `datasets/rating_parameters.json` | Yes | `backend/datasets/rating_parameters.json` | Weighted rules | `RULE_PARAMETERS_PATH` | R |
| `models/models/*.cbm` (4 files) | Yes | `backend/models/models/*.cbm` | Rankers + scorer | `models_dir/models` nested path | R (intentional nesting) |
| `models/training_summary.csv` | Yes | `backend/models/training_summary.csv` | Trees / row counts | Models info / evidence | E |
| `models/gender_evaluation.csv` | Yes | `backend/models/gender_evaluation.csv` | Test metrics | Models info / evidence | E |
| `models/gender_scorer_errors.csv` | Yes | `backend/models/gender_scorer_errors.csv` | Scorer MAE/RMSE | Evidence | E |
| `models/gender_test_predictions.csv` | Yes | `backend/models/gender_test_predictions.csv` | Exported predictions | Inference parity tests | E / T |
| `models/gender_aware_schema.json` | Yes | `backend/models/gender_aware_schema.json` | Runtime schema | `SCHEMA_PATH` default | R |
| `models/run_information.json` | Yes | `backend/models/run_information.json` | Run id + SHA256 | Hash checks / artifact version | R / E |
| Postman collection + env + generator + coverage + README | Yes | `backend/postman/*` | API verification | Not runtime | T |
| `postman/verification_report.md` | Yes | same | Current Newman summary | **Refreshed** to 68/404 | T |
| `postman/newman-report.json` | Yes | same | Current Newman JSON | **Refreshed** (from audit run) | T |
| Historical 58/369 Newman | Yes | `postman/historical/newman_58req_369assert_pre_confidence_aware_folder09/` | Archived stale evidence | Do not use as current proof | T |
| TAF PDF | Yes | `backend/docs/requirements/TAF-J26-IT-403 (version 3) (1) (3).pdf` | Original requirements | — | E |
| Viva / training guides | Yes | `VIVA_EVIDENCE_GUIDE.md`, `training/README.md` | Documentation | — | E |
| `app/`, `tests/`, `requirements.txt`, `.env.example`, `README.md` | Yes | under `backend/` | Application + tests | — | R / T |

### Duplicates / confusion risks

1. **Nested `models/models/`** — intentional; `artifact_loader` loads binaries from `settings.models_dir / "models"`. Do not flatten.
2. **Two `gender_aware_schema.json` files** — `models/` (runtime) includes `gender_feature_used` and `confidence_calibrated`; `datasets/` omits those two keys. Shared feature lists match. Runtime uses **`models/gender_aware_schema.json`**. Documented in `VIVA_EVIDENCE_GUIDE.md`. **No meaningful inference incompatibility.**
3. **Postman historical vs current** — current collection/report/coverage = **68** requests / **404** assertions; archived folder retains **58** / **369**.

No misplaced required runtime binaries or catalogue were found relative to `app/core/paths.py` defaults.

---

## 3. Model and data consistency

### 3.1 Model binaries and hashes (executed)

All four SHA256 values in `models/run_information.json` **match** files under `models/models/`:

| File | Class loaded | Features (12) | Hash match |
|------|--------------|---------------|------------|
| `hair_ranker_gender_aware.cbm` | `CatBoostRanker` | numeric 5 + cats 7 | VERIFIED |
| `beard_ranker_gender_aware.cbm` | `CatBoostRanker` | same order | VERIFIED |
| `grooming_ranker_gender_aware.cbm` | `CatBoostRanker` | same order | VERIFIED |
| `compatibility_scorer_gender_aware.cbm` | `CatBoostRegressor` | same order | VERIFIED |

Feature order (matches schema / API builder):  
`face_length_ratio`, `jaw_width_ratio`, `upper_width_ratio`, `lower_face_ratio`, `symmetry`, `face_shape`, `jawline`, `forehead`, `hairline`, `gender`, `style_id`, `category`.

Categorical indices `[5..11]` = face_shape, jawline, forehead, hairline, gender, style_id, category.  
**Training target `rating` is not a prediction feature.**

Startup log on audit server:  
`artifacts loaded … models=['hair','beard','grooming','compatibility']`; rule parity `checked_rows=84000 mae=0.0 mismatches=0`.

### 3.2 Prediction sample vs export (executed)

Reloaded binaries; compared first rows of `gender_test_predictions.csv`:

- Hair ranker max |Δ| ≈ `1.8e-15`
- Beard / grooming rankers max |Δ| ≈ `1.8e-15` / `4.4e-16`
- Compatibility scorer max |Δ| ≈ `4.4e-16`

**VERIFIED:** exported predictions correspond to the loaded model binaries.

### 3.3 Dataset counts (executed)

| Expectation | Actual | Status |
|-------------|--------|--------|
| 6,000 profiles | 6,000 (3,000 male / 3,000 female) | VERIFIED |
| 16 styles (8/4/4) | catalogue 8 hair, 4 beard, 4 grooming | VERIFIED |
| 84,000 pairs after beard eligibility | `training_pairs` 84,000; female beard rows **0** | VERIFIED |
| Male-only beard training | beard pairs all male (12,000) | VERIFIED |
| Disjoint profile splits | train 4200 / val 900 / test 900 profiles; pairwise disjoint | VERIFIED |
| Pairs stay with profile split | male 16 pairs/profile; female 12; split row/profile ∈ {12,16} | VERIFIED |
| Duplicate profile×style | 0 | VERIFIED |
| Missing required profile fields | 0 | VERIFIED |
| Catalogue IDs = rule style keys | identical H001–H008, B001–B004, G001–G004 | VERIFIED |
| Category weights sum to 1 | hair/beard/grooming all 1.0 | VERIFIED |
| Scales valid | `ratio_scales` all > 0; `symmetry_scale=0.25` | VERIFIED |

`dataset_metadata.json` agrees (`human_reviewed=false`, `expert_validated=false`, `rating_source=rule_generated`).

### 3.4 Evaluation metrics (from `gender_evaluation.csv` — do not relabel as classification accuracy)

These measure **agreement with rule-generated labels**, not human suitability:

| Category | Gender | Ranker top-choice agreement | NDCG@3 | Scorer MAE | Scorer RMSE |
|----------|--------|-----------------------------|--------|------------|-------------|
| hair | male | 0.9557 | 0.9999 | 0.0175 | 0.0217 |
| hair | female | 0.9577 | 0.9998 | 0.0168 | 0.0211 |
| beard | male | 0.9667 | 0.9998 | 0.0252 | 0.0330 |
| grooming | male | 0.9601 | 0.9999 | 0.0173 | 0.0220 |
| grooming | female | 0.9599 | 0.9999 | 0.0183 | 0.0232 |

`training_summary.csv`: hair 1200 trees; beard 893; grooming 596; compatibility 1600; `reload_verified=True` for all.

---

## 4. Notebook / viva evidence audit

**File:** `backend/training/notebooks/Component3_Training_Executed.ipynb`  
**Inspected without re-running all cells.**

| Check | Finding |
|-------|---------|
| Cell count | 101 code cells (no markdown section headers) |
| Outputs present | 91 cells with outputs; 10 without (mostly `%pip`, helpers) |
| `execution_count` | **All null** — do **not** treat filename alone as proof of a clean linear Colab re-run |
| Dataset / gender-aware prep | Present (later cells ~93–94) |
| Profile-level splitting | Uses `profile_id` extensively; not `train_test_split` / `GroupKFold` by name |
| Final four gender-aware models | Cells **95–96**: `CatBoostRanker` ×3 + `CatBoostRegressor`, `save_model`, metrics, export |
| Run id consistency | Cell 97 downloads `Component3_GenderAware_20261008T123658_164628Z.zip` — matches `run_information.json` `run_folder` |
| Evaluation tables in outputs | Cell 96 tables match `gender_evaluation.csv` / scorer errors to displayed precision |
| Historical / experimental cells | Earlier CLIP / IndicFairFace auto-label pipeline; **cell 57** `AttributeError` on CLIP pooling — experimental failure, **not** the final gender-aware training path |
| Earlier ML experiments | Cells ~35–88 contain prior ranker/scorer experiments and metrics; superseded by GenderAware run cells 95–96 |

**PARTIAL for “fully executed notebook”:** substantial outputs exist and final-run artifacts align, but null `execution_count` and mixed experimental history mean the notebook is **viva evidence with caveats**, not a pristine single-pass execution certificate.

**Documentation added:** `backend/training/README.md` clarifies that audit “cells 95–97” are **0-based JSON indices** (1-based positions 96–98), maps final vs experimental cells, and states the CLIP error at index 57 does not invalidate the GenderAware export. Notebook bytes were **not** modified (SHA256 `8362adf763c69182cdfadcc20dd3b6a187c549b2476716328a60db018b5baad8`).

---

## 5. Component 3 behavior (code + live API)

### 5.1 Standard hybrid weights (configured + live)

From `.env.example` / `Settings` defaults and live `/api/v1/capabilities`:

- `predicted_compatibility` = **0.50**
- `rank_percentile` = **0.30**
- `rule_compatibility` = **0.20**

Policy name (default): `hybrid_model_rank_rules_v1`.

### 5.2 Confidence-aware mode (code + live)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Requires all nine facial confidences | VERIFIED | Request validator; live 422 on partial map |
| Gender excluded from facial weighting | VERIFIED | `confidence_aware_rules.facial_confidence_vector` |
| A / S_j / S_j÷A formulas | VERIFIED | `confidence_aware_rules.adjust_rule_evaluation` |
| Only rule term changes in hybrid | VERIFIED | Engine uses adjusted score as rule term only |
| All-zero → standard fallback | VERIFIED | Live: `fallback_applied=true`, support=0, adjusted=null, `review_required` |
| `confidence_source` provenance only | VERIFIED | Tests + policy flag `confidence_source_affects_scores=false` |
| Support ≠ calibrated probability | VERIFIED | Schema/README/notes wording |
| `recommendation_confidence` null / `not_calibrated` | VERIFIED | Live responses |
| Canonical vs deprecated aliases | VERIFIED | Live male request: provided/missing/coverage aliases equal |

Live check (port 8010): all-ones `confidence_aware` reproduced standard hybrid (`0.84796…`) and adjusted rule = original rule (`0.787315`).

### 5.3 Eligibility / validation (tests + live)

- Female beard with `include_beard=true` → `unsupported_model_coverage` (live).
- Unsupported face_shape → 422 (live).
- Finite numeric / confidence bounds covered by `tests/test_validation.py`.

---

## 6. API and test evidence (executed this audit)

### 6.1 OpenAPI paths (live)

`/health/live`, `/health/ready`, `/api/v1/capabilities`, `/api/v1/input-schema`, `/api/v1/styles`, `/api/v1/models/info`, `/api/v1/recommendations`.

### 6.2 pytest (executed)

```text
python -m pytest -q
→ 68 passed, 1 warning (starlette multipart PendingDeprecationWarning)
```

### 6.3 Live scenario checks (port 8010)

All scenarios in `%TEMP%\c3_backend_audit\api_audit_results.json` succeeded as summarized in §5.

### 6.4 Newman

| Metric | Initial audit run (2026-10-13) | After evidence refresh |
|--------|--------------------------------|------------------------|
| Requests | **68** / 0 failed | Same figures now in `postman/newman-report.json` |
| Assertions | **404** / 0 failed | Same |
| Duration | **7986 ms** | Documented in `verification_report.md` |
| Target | `http://127.0.0.1:8010` | Same |
| Collection SHA256 | `9d5ae2a4ab5394562a56beb758c1c4b5adc6242b7a2f85f55cf13308ba776ded` | Recorded in verification report |
| `coverage_matrix.md` | 68 requests / 670 `pm.test` blocks | Consistent |

**Stale 58/369 reports:** archived under `postman/historical/newman_58req_369assert_pre_confidence_aware_folder09/` (not deleted).

Expected HTTP 422 cases in folder 07/09 were treated as passing assertions, not failures.

---

## 7. Requirements status table

| Requirement | Status | File/evidence | Check performed | Remaining action |
|-------------|--------|---------------|-----------------|------------------|
| Structured manual facial profile API | VERIFIED | `schemas/requests.py`, live POST | Schema + live | — |
| Hair/beard/grooming recommendations | VERIFIED | Engine + live male/female | Live categories | — |
| Eligibility filtering | VERIFIED | `eligibility.py`, tests, live female beard | Live + pytest | — |
| Nine-attribute weighted rules | VERIFIED | `rating_parameters.json`, parity mae=0 | Startup + tests | Keep `provisional_unvalidated` disclosure |
| 3 rankers + 1 regressor load | VERIFIED | `models/models/*.cbm`, hashes | Hash + class load | — |
| Hybrid Top-N 0.50/0.30/0.20 | VERIFIED | config + capabilities | Live weights | — |
| Explanations / score terminology | VERIFIED | `explanation_service.py`, response fields | Code + API | — |
| `standard` ranking default | VERIFIED | requests default + live | Live | — |
| Optional `confidence_aware` ranking | VERIFIED | engine + tests + Newman folder 09 | Live + Newman | — |
| No database | VERIFIED | architecture | Inspection | — |
| No image analysis in this component | VERIFIED | README + routes | Inspection | Upstream elsewhere |
| Artifact paths correct | VERIFIED | §2 inventory | Filesystem + paths.py | Clarify dual schema copies in viva |
| Dataset 6k / 84k / 16 styles | VERIFIED | §3.3 | pandas counts | — |
| Split integrity | VERIFIED | §3.3 | profile disjointness | — |
| Prediction parity vs export | VERIFIED | §3.2 | CatBoost reload sample | — |
| Training notebook final run | PARTIAL | notebook cells 95–97 + artifacts | Static inspect | Explain experimental cells; null execution_count |
| Original TAF compliance | BLOCKED | TAF not in repo | Search | Supply TAF if needed for marking |
| Postman verification reports match collection | VERIFIED (after refresh) | `verification_report.md`, `newman-report.json`, historical archive | Newman 68/404 | Keep reports in sync if collection regenerates |
| TAF C3: structured profile + H/B/G options | PARTIAL | TAF p.9; API + catalogue | PDF + live | C2 integration still open |
| TAF C3: hybrid rules + weighted compatibility | VERIFIED | TAF p.9; rules + hybrid | PDF + tests | Research validation open |
| TAF C3: confidence-aware Top-N | PARTIAL | TAF p.9; modes `standard`/`confidence_aware` | PDF + Postman 09 | Calibrated confidence scores not delivered |
| TAF C3: separate category recommendations | VERIFIED | TAF p.9; category results | Live + Postman 03 | — |
| Frontend complete | NOT APPLICABLE | `frontend/` | Listing | Out of scope |
| Integration with other components | MISSING | no Component 2 client wired | Inspection | Upstream contract ready; integration not done |
| Human suitability validation | MISSING | metadata flags false | Metadata | Research unfinished |
| Calibrated recommendation confidence | MISSING | always null / not_calibrated | Live + TAF novelty wording | Research unfinished |

---

## 8. Final conclusions

### A. File organization and artifact consistency

**VERIFIED.** Required runtime and evidence files are in the expected locations. Nested `models/models/` is correctly referenced. Dual schema copies differ only by two metadata keys; runtime uses `models/gender_aware_schema.json`. Model hashes and prediction exports are consistent with `run_information.json`. Schema clarification and viva path docs added.

### B. Backend implementation completeness (agreed engineering scope)

**VERIFIED as complete for the agreed backend engineering scope** documented in README and implemented in `app/`: validation, eligibility, rules, four CatBoost models, hybrid ranking, explanations, standard + confidence-aware modes, capabilities/input-schema, tests, Postman collection.

**Against literal TAF p.9:** engineering tasks largely covered; **calibrated confidence scores** and **live C2 profile intake** remain gaps (see §1.2).

### C. Automated / API verification

**VERIFIED:** pytest **68 passed**; Newman **68 requests / 404 assertions / 0 failed** on port **8010**.  
**Documentation refreshed:** current `newman-report.json` / `verification_report.md` match the collection; historical 58/369 archived.

### D. Training and viva evidence completeness

**PARTIAL.** Final gender-aware cells (0-based 95–97) align with on-disk models/evals; notebook remains a composite Colab history with null `execution_count`. Guidance: `training/README.md` + `VIVA_EVIDENCE_GUIDE.md`.

### E. External-component integration readiness

**PARTIAL / not complete.** Input contract exists. **Component 2 integration is not done.** Manual profile/confidence remain the demo path. **Not marked completed.**

### F. Research validation limitations

**Explicitly unfinished (not marked completed):**

- Ratings are **rule-generated**, not human-reviewed.
- Rule `parameter_status` remains **`provisional_unvalidated`**.
- Metrics are **generated-label agreement**, not human suitability.
- `recommendation_confidence` remains **`null` / `not_calibrated`** despite TAF novelty wording about confidence scores.
- Passing API/Newman/pytest does **not** validate the full research claim.

### Distinctions (required)

| Layer | Status |
|-------|--------|
| Backend engineering (agreed API + models wiring) | Complete (this audit) |
| Frontend | Not in scope / not completed here |
| Actual integration with other components | Not completed |
| Human suitability validation | Not completed |
| Calibrated recommendation confidence | Not completed |

---

## 9. Recommended viva file list

1. `backend/README.md`  
2. `backend/models/run_information.json` + `backend/models/models/*.cbm` (hashes)  
3. `backend/models/gender_evaluation.csv` + `training_summary.csv`  
4. `backend/datasets/dataset_metadata.json` + `rating_parameters.json`  
5. `backend/datasets/generated_data/style_catalogue.csv`  
6. `backend/training/notebooks/Component3_Training_Executed.ipynb` (cells 95–97 + metrics outputs)  
7. `backend/app/services/recommendation_engine.py` + `confidence_aware_rules.py`  
8. Live demos: `/health/ready`, male/female recommendations, `confidence_aware` ones vs zeros  
9. `backend/postman/Component3.postman_collection.json` + this audit’s Newman summary (note stale committed report)  
10. This file: `backend/COMPONENT3_BACKEND_AUDIT.md`

---

## 10. Missing items ordered by importance

1. **Original TAF/proposal not in repo** — cannot close “original requirements” marking without it.  
2. **Refresh stale Postman verification artifacts** (`newman-report.json`, `verification_report.md`) to match the 68-request collection (documentation only).  
3. **Notebook narrative for viva** — separate experimental CLIP failure (cell 57) from final GenderAware run (95–97); acknowledge null execution counts.  
4. **Clarify dual `gender_aware_schema.json` copies** in viva (runtime = `models/`).  
5. **Upstream integration** with Component 2 (future).  
6. **Human suitability study** and **calibrated confidence** (research unfinished).

---

*End of audit report. No application code, datasets, models, notebooks, or prior reports were modified except creation of this file.*
