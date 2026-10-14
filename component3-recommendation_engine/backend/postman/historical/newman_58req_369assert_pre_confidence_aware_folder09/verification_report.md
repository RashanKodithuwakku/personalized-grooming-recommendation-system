# Component 3 Postman Verification Report

**Executed:** yes (Newman CLI against local FastAPI)  
**Date context:** local run after collection generation  
**Target:** `http://127.0.0.1:8000`  
**Environment:** `Component3_Local.postman_environment.json`

## Summary

| Metric | Result |
|--------|--------|
| Requests executed | **58** |
| Requests failed | **0** |
| Assertions executed | **369** |
| Assertions failed | **0** |
| Iterations | 1 |
| Duration | ~5.9s |
| Average response time | ~13ms |

**Overall: PASSED**

## Folder results

| Folder | Status |
|--------|--------|
| 01 - Health and Readiness | Passed |
| 02 - Capabilities, Schema and Catalogue | Passed |
| 03 - Successful Recommendations | Passed |
| 04 - Eligibility and Preferences | Passed |
| 05 - Weighted Rules and Hybrid Ranking | Passed |
| 06 - Confidence and Input Quality | Passed |
| 07 - Validation and Error Handling | Passed |
| 08 - Determinism and Contract Consistency | Passed |

## Fix applied during verification

| Request | Issue | Resolution |
|---------|-------|------------|
| 06.01 | Assertion expected substring `not manufactured`; API note says `No confidence values were manufactured.` | Updated assertion to match actual note text; regenerated collection; reran Newman successfully |

## Not-run / coverage notes

| Item | Status |
|------|--------|
| All 58 collection requests | Executed |
| Authentication flows | N/A (API has none) |
| Database scenarios | N/A (API has none) |
| Unknown `excluded_style_ids` as 422 | Not asserted as failure — implementation ignores unknown IDs (covered by 04.08 as expected 200) |
| Frontend / model binaries / datasets | Not modified |

## Artifacts

- Collection: `backend/postman/Component3.postman_collection.json`
- Environment: `backend/postman/Component3_Local.postman_environment.json`
- Newman JSON report: `backend/postman/newman-report.json`
- Coverage matrix: `backend/postman/coverage_matrix.md`

## Command used

```powershell
cd backend/postman
npx newman run Component3.postman_collection.json `
  -e Component3_Local.postman_environment.json `
  --reporters cli,json `
  --reporter-json-export newman-report.json
```
