# Component 3 Postman Verification Report

**Status:** PASSED (refreshed after `COMPONENT3_BACKEND_AUDIT.md`)  
**Source of counts:** actual Newman JSON export — **not** hand-edited from the old 58/369 report.

## Execution metadata

| Field | Value |
|-------|-------|
| Executed | Yes (Newman CLI) |
| Date context | 2026-10-13 (audit evidence refresh) |
| Target base URL | `http://127.0.0.1:8010` |
| Server | Isolated `uvicorn app.main:app` from this repository on port **8010** |
| Environment file used | Audit override of local env (`base_url` → `8010`); report embeds `base_url=http://127.0.0.1:8010` |
| Collection file | `backend/postman/Component3.postman_collection.json` |
| Collection SHA256 | `9d5ae2a4ab5394562a56beb758c1c4b5adc6242b7a2f85f55cf13308ba776ded` |
| Newman report file | `backend/postman/newman-report.json` (copied from verified audit run) |
| Total run duration | **7986 ms** (~7.99 s) |
| Average response time | ~23.9 ms (min 3 ms, max 163 ms) |

## Actual Newman totals

| Metric | Executed | Failed |
|--------|----------|--------|
| Iterations | 1 | 0 |
| Requests | **68** | **0** |
| Test scripts | 68 | 0 |
| Assertions | **404** | **0** |

These totals match:

- Current collection request count: **68**
- `coverage_matrix.md`: **68** requests / **670** `pm.test` blocks
- Presence of folder **09 - Confidence-Aware Ranking Mode** (requests 09.01–09.07)

## Consistency check vs historical report

| Artifact | Requests | Assertions |
|----------|----------|------------|
| **This report / current `newman-report.json`** | 68 | 404 |
| Archived historical run | 58 | 369 |

Historical files preserved (not deleted) at:

`backend/postman/historical/newman_58req_369assert_pre_confidence_aware_folder09/`

Do **not** treat the archived 58/369 figures as current collection proof.

## Folder results (this run)

| Folder | Result |
|--------|--------|
| 01 - Health and Readiness | Passed |
| 02 - Capabilities, Schema and Catalogue | Passed |
| 03 - Successful Recommendations | Passed |
| 04 - Eligibility and Preferences | Passed |
| 05 - Weighted Rules and Hybrid Ranking | Passed |
| 06 - Confidence and Input Quality | Passed |
| 07 - Validation and Error Handling | Passed (expected 422s asserted as pass) |
| 08 - Determinism and Contract Consistency | Passed |
| 09 - Confidence-Aware Ranking Mode | Passed |

## How to reproduce

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
# other terminal:
cd backend/postman
npx newman run Component3.postman_collection.json `
  -e Component3_Local.postman_environment.json `
  --reporters cli,json `
  --reporter-json-export newman-report.json
```

Set `base_url` in the environment to the port you actually started.
