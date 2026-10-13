# Component 3 Postman Coverage Matrix

Source of truth: FastAPI routes/schemas in `backend/app` and OpenAPI.

- Requests in collection: **68**
- Automated `pm.test` blocks: **670**

| Test ID | Folder / requirement area | Request name | Expected behavior | `pm.test` count |
|---------|---------------------------|--------------|-------------------|-----------------|
| 01.01 | 01 - Health and Readiness | 01.01 GET health live | 200; status=ok | 9 |
| 01.02 | 01 - Health and Readiness | 01.02 GET health ready | ready=true; 4 models; catalogue/schema/rules | 11 |
| 02.01 | 02 - Capabilities, Schema and Catalogue | 02.01 GET capabilities | capabilities + hybrid_model_rank_rules_v1 + not_calibrated | 12 |
| 02.02 | 02 - Capabilities, Schema and Catalogue | 02.02 GET input-schema | schema_version 1.0; top_n max 20 | 9 |
| 02.03 | 02 - Capabilities, Schema and Catalogue | 02.03 GET styles full catalogue | 16 unique styles H001–H008/B001–B004/G001–G004 | 10 |
| 02.04 | 02 - Capabilities, Schema and Catalogue | 02.04 GET styles category=hair | 8 hair styles | 9 |
| 02.05 | 02 - Capabilities, Schema and Catalogue | 02.05 GET styles category=beard | 4 beard styles; B001 clean-shaven; B002 requires facial hair | 9 |
| 02.06 | 02 - Capabilities, Schema and Catalogue | 02.06 GET styles category=grooming | 4 grooming styles | 9 |
| 02.07 | 02 - Capabilities, Schema and Catalogue | 02.07 GET styles unsupported category | HTTP 422 | 9 |
| 02.08 | 02 - Capabilities, Schema and Catalogue | 02.08 GET models info | 4 models; confidence_calibrated=false; no paths | 11 |
| 03.01 | 03 - Successful Recommendations | 03.01 Male hair+beard+grooming top_n=3 | 200; hair/beard/grooming ok; scores finite; rules present | 14 |
| 03.02 | 03 - Successful Recommendations | 03.02 Female hair+grooming (beard default skipped) | hair/grooming ok; beard default_gender_policy | 14 |
| 03.03 | 03 - Successful Recommendations | 03.03 Male hair only | hair ok | 14 |
| 03.04 | 03 - Successful Recommendations | 03.04 Male beard only | beard ok | 14 |
| 03.05 | 03 - Successful Recommendations | 03.05 Grooming only | grooming ok | 14 |
| 03.06 | 03 - Successful Recommendations | 03.06 Male top_n=1 | returned_count <= 1 | 14 |
| 03.07 | 03 - Successful Recommendations | 03.07 Male top_n=3 (explicit) | returned_count <= 3 | 14 |
| 03.08 | 03 - Successful Recommendations | 03.08 top_n greater than eligible (grooming top_n=20) | returned_count == eligible_count == 4 | 14 |
| 04.01 | 04 - Eligibility and Preferences | 04.01 Female all categories default beard skip | beard default_gender_policy; others ok | 10 |
| 04.02 | 04 - Eligibility and Preferences | 04.02 Female include_beard=true unsupported coverage | beard unsupported_model_coverage; others ok | 10 |
| 04.03 | 04 - Eligibility and Preferences | 04.03 Male include_beard=false | beard excluded_by_preference | 9 |
| 04.04 | 04 - Eligibility and Preferences | 04.04 facial_hair_available=false keeps clean-shaven only | only B001; requires_facial_hair=false | 9 |
| 04.05 | 04 - Eligibility and Preferences | 04.05 Exclude one known style H001 | H001 excluded; not reintroduced | 9 |
| 04.06 | 04 - Eligibility and Preferences | 04.06 Exclude multiple known styles | H001–H003 excluded | 9 |
| 04.07 | 04 - Eligibility and Preferences | 04.07 Exclude every grooming style -> empty category | status=empty with reason | 9 |
| 04.08 | 04 - Eligibility and Preferences | 04.08 Unknown excluded style ID is ignored (not a validation error) | 200; unknown exclusion ignored | 9 |
| 05.01 | 05 - Weighted Rules and Hybrid Ranking | 05.01 Verify hybrid weights and score scales | weights 0.5/0.3/0.2; rescale; hybrid math; 9 contribs | 11 |
| 05.02 | 05 - Weighted Rules and Hybrid Ranking | 05.02 Independent H001 perfect-match rule calculation | H001 rule score ≈ 1.0 from rating_parameters.json | 11 |
| 05.03 | 05 - Weighted Rules and Hybrid Ranking | 05.03 Ordering follows hybrid_score then style_id | hybrid desc + style_id tie-break | 9 |
| 06.01 | 06 - Confidence and Input Quality | 06.01 attribute_confidence omitted | confidence_status=not_provided; score null | 11 |
| 06.02 | 06 - Confidence and Input Quality | 06.02 Complete high confidence -> standard | confidence_status=provided; recommendation_confidence null | 9 |
| 06.03 | 06 - Confidence and Input Quality | 06.03 Partial confidence map | partial coverage < 1 | 9 |
| 06.04 | 06 - Confidence and Input Quality | 06.04 Complete low confidence -> review_required | caution_flag; low_confidence_attributes | 9 |
| 06.05 | 06 - Confidence and Input Quality | 06.05 Gender confidence alone does not count as facial coverage | 0 and 1 accepted | 9 |
| 06.06 | 06 - Confidence and Input Quality | 06.06 Boundary confidence 0 and 1 in partial map | See scripts | 9 |
| 06.07 | 06 - Confidence and Input Quality | 06.07 Store low-confidence hybrid order | See scripts | 9 |
| 06.08 | 06 - Confidence and Input Quality | 06.08 Compare no-confidence order to 06.07 | See scripts | 11 |
| 07.01 | 07 - Validation and Error Handling | 07.01 Missing required profile field (face_shape) | HTTP 422 structured detail | 9 |
| 07.02 | 07 - Validation and Error Handling | 07.02 Unsupported face_shape | HTTP 422 | 9 |
| 07.03 | 07 - Validation and Error Handling | 07.03 Unsupported jawline | HTTP 422 | 9 |
| 07.04 | 07 - Validation and Error Handling | 07.04 Unsupported forehead | HTTP 422 | 9 |
| 07.05 | 07 - Validation and Error Handling | 07.05 Unsupported hairline | HTTP 422 | 9 |
| 07.06 | 07 - Validation and Error Handling | 07.06 Unsupported gender | HTTP 422 | 9 |
| 07.07 | 07 - Validation and Error Handling | 07.07 Invalid numeric type | HTTP 422 | 9 |
| 07.08 | 07 - Validation and Error Handling | 07.08 Symmetry below 0 | HTTP 422 | 9 |
| 07.09 | 07 - Validation and Error Handling | 07.09 Symmetry above 1 | HTTP 422 | 9 |
| 07.10 | 07 - Validation and Error Handling | 07.10 Confidence below 0 | HTTP 422 | 9 |
| 07.11 | 07 - Validation and Error Handling | 07.11 Confidence above 1 | HTTP 422 | 9 |
| 07.12 | 07 - Validation and Error Handling | 07.12 Invalid category | HTTP 422 | 9 |
| 07.13 | 07 - Validation and Error Handling | 07.13 top_n=0 | HTTP 422 | 9 |
| 07.14 | 07 - Validation and Error Handling | 07.14 Negative top_n | HTTP 422 | 9 |
| 07.15 | 07 - Validation and Error Handling | 07.15 top_n above configured maximum (21 > max_top_n=20) | HTTP 422 (max_top_n=20) | 9 |
| 07.16 | 07 - Validation and Error Handling | 07.16 top_n above schema hard max (51) | HTTP 422 (schema le=50) | 9 |
| 07.17 | 07 - Validation and Error Handling | 07.17 Unknown confidence attribute | HTTP 422 | 9 |
| 07.18 | 07 - Validation and Error Handling | 07.18 Malformed JSON | HTTP 422 | 9 |
| 07.19 | 07 - Validation and Error Handling | 07.19 Unknown top-level field (extra=forbid) | HTTP 422 extra=forbid | 9 |
| 07.20 | 07 - Validation and Error Handling | 07.20 Empty categories list | HTTP 422 | 9 |
| 07.21 | 07 - Validation and Error Handling | 07.21 NaN symmetry rejected | HTTP 422 | 9 |
| 07.22 | 07 - Validation and Error Handling | 07.22 Infinity face_length_ratio rejected | HTTP 422 | 8 |
| 08.01 | 08 - Determinism and Contract Consistency | 08.01 Determinism baseline (store stable fields) | store stable fields | 9 |
| 08.02 | 08 - Determinism and Contract Consistency | 08.02 Determinism compare (identical request) | identical stable recommendation fields | 11 |
| 09.01 | 09 - Confidence-Aware Ranking Mode | 09.01 Standard mode (explicit) | See scripts | 9 |
| 09.02 | 09 - Confidence-Aware Ranking Mode | 09.02 Confidence-aware all confidences = 1 | See scripts | 9 |
| 09.03 | 09 - Confidence-Aware Ranking Mode | 09.03 Same profile, low face_shape confidence | See scripts | 9 |
| 09.04 | 09 - Confidence-Aware Ranking Mode | 09.04 Same profile, low jawline confidence | See scripts | 9 |
| 09.05 | 09 - Confidence-Aware Ranking Mode | 09.05 Uniform low confidence | See scripts | 9 |
| 09.06 | 09 - Confidence-Aware Ranking Mode | 09.06 All-zero confidence fallback | See scripts | 9 |
| 09.07 | 09 - Confidence-Aware Ranking Mode | 09.07 Incomplete confidence map rejected | See scripts | 8 |

## Notes

- Unknown `excluded_style_ids` are **not** validation errors in the current API; they are ignored during filtering (covered by 04.08).
- `top_n` Pydantic bound is `1..50`, but runtime `max_top_n` default is **20** (covered by 07.15 vs 07.16).
- Raw ranker scores are **not** asserted as probabilities.
- H001 independent rule fixture uses exact targets from `datasets/rating_parameters.json`.
- Determinism pair 08.01 → 08.02 must run in order; variables are cleared after 08.02.
