# Component 3 Postman Collection

Executable Postman Collection v2.1 for the Style Recommendation and Ranking Engine (FastAPI).

## Files

| File | Purpose |
|------|---------|
| `Component3.postman_collection.json` | Collection with folders, bodies, and `pm.test` scripts (**68** requests) |
| `Component3_Local.postman_environment.json` | Local environment (`base_url`) |
| `coverage_matrix.md` | Requirement → request → assertion map (**68** / **670** `pm.test` blocks) |
| `verification_report.md` | Latest Newman execution summary (**68** req / **404** assertions) |
| `newman-report.json` | Latest Newman JSON export matching the current collection |
| `generate_collection.py` | Regenerates collection/environment/coverage from code |
| `historical/newman_58req_369assert_pre_confidence_aware_folder09/` | Archived pre–folder-09 evidence (**58** / **369**); do not use as current proof |

## Import into Postman

1. Open Postman → **Import**.
2. Select:
   - `backend/postman/Component3.postman_collection.json`
   - `backend/postman/Component3_Local.postman_environment.json`
3. In the environment dropdown (top-right), select **Component3_Local**.
4. Confirm `base_url` = `http://127.0.0.1:8000`.

## Start the backend

From `backend/`:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check readiness:

```powershell
curl.exe http://127.0.0.1:8000/health/ready
```

Expect `ready: true`, all four models loaded, and `rules_available: true`.

Swagger UI: http://127.0.0.1:8000/docs

## Run one request

1. Select environment **Component3_Local**.
2. Open folder **01 - Health and Readiness**.
3. Send **01.02 GET health ready**.
4. Confirm Test Results are green.

## Run the full Collection Runner

1. Open the collection → **Run**.
2. Select environment **Component3_Local**.
3. Keep request order (required for **08.01 → 08.02** determinism pair).
4. Delay: optional `0–100 ms`.
5. Click **Run Component 3…**.

Notes:

- Ordinary requests are independently runnable.
- **08.02** depends on collection variables set by **08.01** in the same run.
- No authentication variables are required.

## CLI execution with Newman

Install Newman (once):

```powershell
npm install -g newman
```

From `backend/postman/`:

```powershell
newman run Component3.postman_collection.json `
  -e Component3_Local.postman_environment.json `
  --reporters cli,json `
  --reporter-json-export newman-report.json
```

Or from `backend/`:

```powershell
newman run postman/Component3.postman_collection.json -e postman/Component3_Local.postman_environment.json
```

## Expected behavior summary

| Area | Expected |
|------|----------|
| Health | live `status=ok`; ready `ready=true` with 4 models + rules |
| Catalogue | 16 styles: H001–H008, B001–B004, G001–G004 |
| Male recommendations | hair/beard/grooming with rule contributions |
| Female default | beard `default_gender_policy`; hair/grooming continue |
| Female `include_beard=true` | beard `unsupported_model_coverage` |
| Hybrid policy | `hybrid_model_rank_rules_v1` weights 0.50 / 0.30 / 0.20 |
| Confidence omitted | `input_quality_score=null`, `not_provided`, `assessment=unknown`, disposition `review_required` |
| Complete high confidence | `assessment=adequate`, disposition `standard` |
| Partial / low confidence | `review_required`; hybrid ordering unchanged in `ranking_mode=standard` |
| `ranking_mode=confidence_aware` | Folder 09; requires all nine facial confidences; policy `hybrid_confidence_adjusted_rules_v1` |
| Validation failures | HTTP **422** with structured `detail` |
| Determinism | identical stable scores/order for repeated request |

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Connection refused | Backend not running on port 8000 |
| ready=false | Models/catalogue/rules failed to load; see `/health/ready` diagnostics |
| Many 422 on valid bodies | Wrong environment / wrong `base_url` |
| 08.02 fails alone | Run full collection so 08.01 stores baseline first |
| top_n=21 fails | Expected: runtime `max_top_n` default is **20** |
| Unknown excluded style passes | Expected: unknown IDs are ignored, not rejected |

## Regenerating the collection

If routes/schemas change:

```powershell
cd backend
python postman/generate_collection.py
```

Do not store model binaries or datasets inside the collection.
