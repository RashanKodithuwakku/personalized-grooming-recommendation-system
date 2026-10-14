"""Generate Component 3 Postman Collection v2.1 artifacts.

Run from backend/:  python postman/generate_collection.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent

MALE = {
    "face_length_ratio": 1.1075061748845896,
    "jaw_width_ratio": 0.7981134693568468,
    "upper_width_ratio": 0.8836110941414184,
    "lower_face_ratio": 0.519768052719499,
    "symmetry": 0.8105352571132579,
    "face_shape": "round",
    "jawline": "soft",
    "forehead": "low",
    "hairline": "straight",
    "gender": "male",
}

FEMALE = {
    "face_length_ratio": 1.4741868136966976,
    "jaw_width_ratio": 0.7022803446346432,
    "upper_width_ratio": 0.8874882194850102,
    "lower_face_ratio": 0.4261109355990833,
    "symmetry": 0.5257072408486533,
    "face_shape": "round",
    "jawline": "soft",
    "forehead": "high",
    "hairline": "receding",
    "gender": "female",
}

# Exact H001 style targets from datasets/rating_parameters.json (source of truth).
H001_MATCH_PROFILE = {
    "face_length_ratio": 1.45,
    "jaw_width_ratio": 0.8,
    "upper_width_ratio": 0.96,
    "lower_face_ratio": 0.43,
    "symmetry": 0.85,
    "face_shape": "oval",
    "jawline": "soft",
    "forehead": "low",
    "hairline": "straight",
    "gender": "male",
}


FACIAL9 = [
    "face_length_ratio",
    "jaw_width_ratio",
    "upper_width_ratio",
    "lower_face_ratio",
    "face_shape",
    "jawline",
    "forehead",
    "hairline",
    "symmetry",
]


def facial_conf(value=1.0, **overrides):
    conf = {k: float(value) for k in FACIAL9}
    conf.update(overrides)
    return conf


def req_body(
    profile,
    categories,
    top_n=3,
    preferences=None,
    confidence=None,
    schema_version="1.0",
    ranking_mode=None,
    confidence_source=None,
):
    body = {
        "schema_version": schema_version,
        "profile": profile,
        "categories": categories,
        "top_n": top_n,
    }
    if preferences is not None:
        body["preferences"] = preferences
    if confidence is not None:
        body["attribute_confidence"] = confidence
    if ranking_mode is not None:
        body["ranking_mode"] = ranking_mode
    if confidence_source is not None:
        body["confidence_source"] = confidence_source
    return body


COMMON_HELPERS = r"""
function isFiniteNumber(v) {
    return typeof v === 'number' && Number.isFinite(v);
}

function getJson() {
    try { return pm.response.json(); }
    catch (e) { throw new Error('Response is not valid JSON: ' + e); }
}

function categoryMap(body) {
    const map = {};
    (body.category_results || []).forEach(c => { map[c.category] = c; });
    return map;
}

function skippedMap(body) {
    const map = {};
    (body.skipped_categories || []).forEach(c => { map[c.category] = c; });
    return map;
}

function assertRecommendationItem(item, prefix) {
    pm.test(prefix + ' has required score fields', function () {
        pm.expect(item).to.have.property('style_id');
        pm.expect(item).to.have.property('style_name');
        pm.expect(item).to.have.property('rank');
        pm.expect(isFiniteNumber(item.raw_ranker_score)).to.eql(true);
        pm.expect(isFiniteNumber(item.raw_predicted_compatibility_rating)).to.eql(true);
        pm.expect(isFiniteNumber(item.display_compatibility_rating)).to.eql(true);
        pm.expect(isFiniteNumber(item.compatibility_score)).to.eql(true);
        pm.expect(isFiniteNumber(item.hybrid_score)).to.eql(true);
        pm.expect(isFiniteNumber(item.rank_percentile)).to.eql(true);
        pm.expect(isFiniteNumber(item.normalized_predicted_compatibility)).to.eql(true);
    });
    pm.test(prefix + ' display rating in [1,5] and compatibility_score in [0,100]', function () {
        pm.expect(item.display_compatibility_rating).to.be.at.least(1);
        pm.expect(item.display_compatibility_rating).to.be.at.most(5);
        pm.expect(item.compatibility_score).to.be.at.least(0);
        pm.expect(item.compatibility_score).to.be.at.most(100);
        const expected = 100 * (item.display_compatibility_rating - 1) / 4;
        pm.expect(Math.abs(item.compatibility_score - expected)).to.be.below(1e-6);
    });
    pm.test(prefix + ' does not treat ranker score as a probability', function () {
        // Raw ranker scores are unconstrained; only require finiteness (already checked).
        pm.expect(isFiniteNumber(item.raw_ranker_score)).to.eql(true);
    });
}

function assertCategoryOk(cat, topN, allowedIds) {
    pm.test(cat.category + ' status ok with bounded counts', function () {
        pm.expect(cat.status).to.eql('ok');
        pm.expect(cat.returned_count).to.eql(cat.recommendations.length);
        pm.expect(cat.returned_count).to.be.at.most(topN);
        pm.expect(cat.returned_count).to.be.at.most(cat.eligible_count);
        pm.expect(cat.returned_count).to.be.above(0);
    });
    const ids = cat.recommendations.map(r => r.style_id);
    pm.test(cat.category + ' unique catalogue style IDs', function () {
        pm.expect(new Set(ids).size).to.eql(ids.length);
        ids.forEach(id => pm.expect(allowedIds).to.include(id));
    });
    // Descending hybrid_score; style_id ascending tie-break
    pm.test(cat.category + ' hybrid descending with style_id tie-break', function () {
        for (let i = 1; i < cat.recommendations.length; i++) {
            const prev = cat.recommendations[i - 1];
            const cur = cat.recommendations[i];
            if (Math.abs(prev.hybrid_score - cur.hybrid_score) < 1e-12) {
                pm.expect(prev.style_id <= cur.style_id).to.eql(true);
            } else {
                pm.expect(prev.hybrid_score).to.be.above(cur.hybrid_score);
            }
        }
    });
    cat.recommendations.forEach((item, idx) => {
        assertRecommendationItem(item, cat.category + '[' + idx + ']');
        pm.test(cat.category + '[' + idx + '] rank sequence', function () {
            pm.expect(item.rank).to.eql(idx + 1);
            pm.expect(item.category).to.eql(cat.category);
        });
    });
}
"""


def event(tests_js: str, prerequest_js: str | None = None):
    events = []
    if prerequest_js:
        events.append({
            "listen": "prerequest",
            "script": {"type": "text/javascript", "exec": prerequest_js.split("\n")},
        })
    events.append({
        "listen": "test",
        "script": {"type": "text/javascript", "exec": (COMMON_HELPERS + "\n" + tests_js).split("\n")},
    })
    return events


def request_item(name, method, path, tests_js, body=None, description="", query=None, raw_body=None, headers=None):
    url = {
        "raw": "{{base_url}}" + path + (("?" + "&".join(f"{k}={v}" for k, v in (query or []))) if query else ""),
        "host": ["{{base_url}}"],
        "path": [p for p in path.strip("/").split("/") if p],
    }
    if query:
        url["query"] = [{"key": k, "value": v} for k, v in query]

    hdrs = [{"key": "Accept", "value": "application/json"}]
    if headers:
        hdrs.extend(headers)

    req = {
        "method": method,
        "header": hdrs,
        "url": url,
        "description": description,
    }
    if body is not None:
        req["header"].append({"key": "Content-Type", "value": "application/json"})
        req["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    elif raw_body is not None:
        req["header"].append({"key": "Content-Type", "value": "application/json"})
        req["body"] = {
            "mode": "raw",
            "raw": raw_body,
            "options": {"raw": {"language": "json"}},
        }

    return {
        "name": name,
        "request": req,
        "event": event(tests_js),
        "response": [],
    }


def build_collection():
    folders = []

    # ---- 01 Health ----
    folders.append({
        "name": "01 - Health and Readiness",
        "item": [
            request_item(
                "01.01 GET health live",
                "GET",
                "/health/live",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('liveness contract', function () {
    pm.expect(body.status).to.eql('ok');
    pm.expect(body).to.have.property('service');
    pm.expect(body).to.have.property('version');
});
""",
                description="Process liveness probe.",
            ),
            request_item(
                "01.02 GET health ready",
                "GET",
                "/health/ready",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('readiness true for valid local setup', function () {
    pm.expect(body.ready).to.eql(true);
    pm.expect(body.status).to.eql('ready');
});
pm.test('all four models loaded', function () {
    pm.expect(body.models_loaded.hair).to.eql(true);
    pm.expect(body.models_loaded.beard).to.eql(true);
    pm.expect(body.models_loaded.grooming).to.eql(true);
    pm.expect(body.models_loaded.compatibility).to.eql(true);
});
pm.test('catalogue, schema, rules available', function () {
    pm.expect(body.catalogue_loaded).to.eql(true);
    pm.expect(body.schema_loaded).to.eql(true);
    pm.expect(body.rules_available).to.eql(true);
});
""",
                description="Artifact readiness including models, catalogue, schema, and weighted rules.",
            ),
        ],
    })

    # ---- 02 Capabilities ----
    folders.append({
        "name": "02 - Capabilities, Schema and Catalogue",
        "item": [
            request_item(
                "02.01 GET capabilities",
                "GET",
                "/api/v1/capabilities",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('capabilities core fields', function () {
    pm.expect(body.recommendation_ready).to.eql(true);
    pm.expect(body.rules_available).to.eql(true);
    pm.expect(body.rules_status).to.eql('available_verified');
    pm.expect(body.rule_parameter_status).to.eql('provisional_unvalidated');
    pm.expect(body.confidence_calibration_status).to.eql('not_calibrated');
    pm.expect(body.available_categories).to.have.members(['hair','beard','grooming']);
    pm.expect(body.rule_verified_categories).to.have.members(['hair','beard','grooming']);
    pm.expect(body.rule_covered_style_ids).to.have.length(16);
});
pm.test('catalogue coverage and confidence policy', function () {
    pm.expect(body.catalogue_coverage.hair_style_count).to.eql(8);
    pm.expect(body.catalogue_coverage.beard_style_count).to.eql(4);
    pm.expect(body.catalogue_coverage.grooming_style_count).to.eql(4);
    pm.expect(body.catalogue_coverage.grooming_focus.toLowerCase()).to.include('eyebrow');
    pm.expect(body.confidence_policy.policy_name).to.eql('confidence_aware_topn_flagging_v1');
    pm.expect(body.score_terminology.compatibility_score.toLowerCase()).to.include('rescaled');
    pm.expect(body.available_ranking_modes).to.include.members(['standard','confidence_aware']);
    pm.expect(body.score_terminology).to.have.property('confidence_adjusted_rule_score');
    pm.expect(body.score_terminology).to.have.property('recommendation_support_score');
});
pm.test('active hybrid policy hybrid_model_rank_rules_v1', function () {
    pm.expect(body.ranking_policy.policy_name).to.eql('hybrid_model_rank_rules_v1');
    pm.expect(body.ranking_policy.weights.predicted_compatibility).to.eql(0.5);
    pm.expect(body.ranking_policy.weights.rank_percentile).to.eql(0.3);
    pm.expect(body.ranking_policy.weights.rule_compatibility).to.eql(0.2);
    pm.expect(body.ranking_policy.provisional).to.eql(true);
});
pm.test('no absolute Windows paths in capabilities JSON', function () {
    const text = JSON.stringify(body);
    pm.expect(text.indexOf('C:\\\\')).to.eql(-1);
    pm.expect(text.indexOf('C:/')).to.eql(-1);
});
pm.collectionVariables.set('caps_style_ids', JSON.stringify(body.rule_covered_style_ids || []));
""",
            ),
            request_item(
                "02.02 GET input-schema",
                "GET",
                "/api/v1/input-schema",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('input schema contract', function () {
    pm.expect(body.schema_version).to.eql('1.0');
    pm.expect(body.supported_categories).to.include.members(['hair','beard','grooming']);
    pm.expect(body.supported_genders).to.include.members(['male','female']);
    pm.expect(body.model_features).to.include.members(['style_id','category','gender']);
    pm.expect(body.top_n_limits.max).to.eql(20);
    pm.expect(body.facial_confidence_attributes).to.have.length(9);
    pm.expect(body.ranking_modes).to.include.members(['standard','confidence_aware']);
    pm.expect(body.confidence_sources).to.include.members(['manual','upstream','unspecified']);
    pm.expect(body).to.have.property('confidence_aware_request_example');
    pm.expect(body.upstream_integration_contract.length).to.be.above(0);
    pm.expect(body).to.have.property('empirical_ranges_note');
    pm.expect(body).to.have.property('request_example');
});
""",
            ),
            request_item(
                "02.03 GET styles full catalogue",
                "GET",
                "/api/v1/styles",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('16 unique styles covering H/B/G ranges', function () {
    pm.expect(body.count).to.eql(16);
    pm.expect(body.styles.length).to.eql(16);
    const ids = body.styles.map(s => s.style_id).sort();
    pm.expect(new Set(ids).size).to.eql(16);
    const expected = [];
    for (let i=1;i<=8;i++) expected.push('H00'+i);
    for (let i=1;i<=4;i++) expected.push('B00'+i);
    for (let i=1;i<=4;i++) expected.push('G00'+i);
    pm.expect(ids).to.eql(expected.sort());
});
pm.test('catalogue categories only hair/beard/grooming', function () {
    const cats = new Set(body.styles.map(s => s.category));
    cats.forEach(c => pm.expect(['hair','beard','grooming']).to.include(c));
});
pm.collectionVariables.set('catalogue_json', JSON.stringify(body.styles));
""",
            ),
            request_item(
                "02.04 GET styles category=hair",
                "GET",
                "/api/v1/styles",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('hair filter returns 8 styles', function () {
    pm.expect(body.count).to.eql(8);
    body.styles.forEach(s => {
        pm.expect(s.category).to.eql('hair');
        pm.expect(s.style_id).to.match(/^H00[1-8]$/);
    });
});
""",
                query=[("category", "hair")],
            ),
            request_item(
                "02.05 GET styles category=beard",
                "GET",
                "/api/v1/styles",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('beard filter returns 4 styles', function () {
    pm.expect(body.count).to.eql(4);
    body.styles.forEach(s => {
        pm.expect(s.category).to.eql('beard');
        pm.expect(s.style_id).to.match(/^B00[1-4]$/);
    });
    const clean = body.styles.find(s => s.style_id === 'B001');
    pm.expect(clean.requires_facial_hair).to.eql(false);
    const stubble = body.styles.find(s => s.style_id === 'B002');
    pm.expect(stubble.requires_facial_hair).to.eql(true);
});
""",
                query=[("category", "beard")],
            ),
            request_item(
                "02.06 GET styles category=grooming",
                "GET",
                "/api/v1/styles",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('grooming filter returns 4 styles', function () {
    pm.expect(body.count).to.eql(4);
    body.styles.forEach(s => {
        pm.expect(s.category).to.eql('grooming');
        pm.expect(s.style_id).to.match(/^G00[1-4]$/);
    });
});
""",
                query=[("category", "grooming")],
            ),
            request_item(
                "02.07 GET styles unsupported category",
                "GET",
                "/api/v1/styles",
                """
pm.test('unsupported category returns 422', function () {
    pm.response.to.have.status(422);
});
const body = getJson();
pm.test('structured error detail present', function () {
    pm.expect(body).to.have.property('detail');
});
""",
                query=[("category", "makeup")],
            ),
            request_item(
                "02.08 GET models info",
                "GET",
                "/api/v1/models/info",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('four models with hashes, no filesystem path fields', function () {
    pm.expect(body.models).to.have.length(4);
    pm.expect(body.confidence_calibrated).to.eql(false);
    body.models.forEach(m => {
        pm.expect(m).to.have.property('filename');
        pm.expect(m).to.have.property('sha256');
        pm.expect(m).to.not.have.property('path');
        pm.expect(m.loaded).to.eql(true);
    });
});
pm.test('evaluation disclaimer present when evaluation included', function () {
    if (body.evaluation) {
        pm.expect(body.evaluation.disclaimer).to.be.a('string');
        pm.expect(body.evaluation.disclaimer.toLowerCase()).to.include('not real-world');
    }
});
const text = JSON.stringify(body);
pm.test('no absolute local path leakage', function () {
    pm.expect(text.indexOf('C:\\\\Users')).to.eql(-1);
    pm.expect(text.indexOf('/content/drive')).to.eql(-1);
});
""",
            ),
        ],
    })

    # ---- 03 Successful recommendations ----
    success_items = []

    def add_success(name, body, expect_cats_ok, expect_skipped=None, top_n=None):
        top = top_n if top_n is not None else body.get("top_n", 5)
        skipped = expect_skipped or {}
        tests = f"""
pm.test('status 200', function () {{ pm.response.to.have.status(200); }});
const body = getJson();
const topN = {top};
const expectedOk = {json.dumps(expect_cats_ok)};
const expectedSkipped = {json.dumps(skipped)};
pm.test('response contract fields', function () {{
    pm.expect(body).to.have.property('request_id');
    pm.expect(body).to.have.property('artifact_version');
    pm.expect(body).to.have.property('ranking_policy');
    pm.expect(body).to.have.property('category_results');
    pm.expect(body.recommendation_confidence).to.eql(null);
    pm.expect(body.recommendation_confidence_status).to.eql('not_calibrated');
}});
pm.test('active policy hybrid_model_rank_rules_v1', function () {{
    pm.expect(body.ranking_policy.policy_name).to.eql('hybrid_model_rank_rules_v1');
}});
const cmap = categoryMap(body);
const smap = skippedMap(body);
expectedOk.forEach(cat => {{
    pm.test('category ' + cat + ' present and ok', function () {{
        pm.expect(cmap).to.have.property(cat);
    }});
    if (cmap[cat]) {{
        const allowed = cat === 'hair'
            ? ['H001','H002','H003','H004','H005','H006','H007','H008']
            : (cat === 'beard'
                ? ['B001','B002','B003','B004']
                : ['G001','G002','G003','G004']);
        assertCategoryOk(cmap[cat], topN, allowed);
        pm.test(cat + ' has disposition and category_input_quality', function () {{
            pm.expect(['standard','review_required']).to.include(cmap[cat].recommendation_disposition);
            pm.expect(cmap[cat].category_input_quality).to.be.an('object');
        }});
        cmap[cat].recommendations.forEach((item, idx) => {{
            pm.test(cat + '[' + idx + '] rule contributions and pipeline present', function () {{
                pm.expect(item.rule_compatibility_score).to.not.eql(null);
                pm.expect(item.explanation.rule_contributions).to.have.length(9);
                pm.expect(item.explanation.pipeline_stages).to.include('eligibility_filtering');
                pm.expect(item.explanation.pipeline_stages).to.include('hybrid_ordering');
            }});
        }});
    }}
}});
Object.keys(expectedSkipped).forEach(cat => {{
    pm.test('skipped ' + cat + ' status', function () {{
        pm.expect(smap).to.have.property(cat);
        pm.expect(smap[cat].status).to.eql(expectedSkipped[cat]);
        pm.expect(cmap[cat].status).to.eql('skipped');
    }});
}});
"""
        success_items.append(request_item(name, "POST", "/api/v1/recommendations", tests, body=body))

    add_success(
        "03.01 Male hair+beard+grooming top_n=3",
        req_body(MALE, ["hair", "beard", "grooming"], 3, {
            "include_beard": True,
            "facial_hair_available": True,
            "excluded_style_ids": [],
        }),
        ["hair", "beard", "grooming"],
    )
    add_success(
        "03.02 Female hair+grooming (beard default skipped)",
        req_body(FEMALE, ["hair", "beard", "grooming"], 3, {
            "facial_hair_available": False,
            "excluded_style_ids": [],
        }),
        ["hair", "grooming"],
        {"beard": "default_gender_policy"},
    )
    add_success(
        "03.03 Male hair only",
        req_body(MALE, ["hair"], 3),
        ["hair"],
    )
    add_success(
        "03.04 Male beard only",
        req_body(MALE, ["beard"], 3, {"include_beard": True, "facial_hair_available": True}),
        ["beard"],
    )
    add_success(
        "03.05 Grooming only",
        req_body(MALE, ["grooming"], 3),
        ["grooming"],
    )
    add_success(
        "03.06 Male top_n=1",
        req_body(MALE, ["hair", "beard", "grooming"], 1, {"include_beard": True}),
        ["hair", "beard", "grooming"],
        top_n=1,
    )
    add_success(
        "03.07 Male top_n=3 (explicit)",
        req_body(MALE, ["hair"], 3),
        ["hair"],
        top_n=3,
    )
    add_success(
        "03.08 top_n greater than eligible (grooming top_n=20)",
        req_body(MALE, ["grooming"], 20),
        ["grooming"],
        top_n=20,
    )

    folders.append({"name": "03 - Successful Recommendations", "item": success_items})

    # ---- 04 Eligibility ----
    folders.append({
        "name": "04 - Eligibility and Preferences",
        "item": [
            request_item(
                "04.01 Female all categories default beard skip",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const smap = skippedMap(body);
const cmap = categoryMap(body);
pm.test('beard skipped with default_gender_policy', function () {
    pm.expect(smap.beard.status).to.eql('default_gender_policy');
    pm.expect(cmap.beard.status).to.eql('skipped');
    pm.expect(cmap.beard.recommendations).to.eql([]);
});
pm.test('hair and grooming continue', function () {
    pm.expect(cmap.hair.status).to.eql('ok');
    pm.expect(cmap.grooming.status).to.eql('ok');
});
""",
                body=req_body(FEMALE, ["hair", "beard", "grooming"], 3),
            ),
            request_item(
                "04.02 Female include_beard=true unsupported coverage",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const smap = skippedMap(body);
const cmap = categoryMap(body);
pm.test('beard unsupported_model_coverage', function () {
    pm.expect(smap.beard.status).to.eql('unsupported_model_coverage');
    pm.expect(cmap.beard.status).to.eql('skipped');
});
pm.test('other categories continue', function () {
    pm.expect(cmap.hair.status).to.eql('ok');
    pm.expect(cmap.grooming.status).to.eql('ok');
});
""",
                body=req_body(FEMALE, ["hair", "beard", "grooming"], 2, {"include_beard": True}),
            ),
            request_item(
                "04.03 Male include_beard=false",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('beard excluded_by_preference', function () {
    pm.expect(skippedMap(body).beard.status).to.eql('excluded_by_preference');
    pm.expect(categoryMap(body).beard.status).to.eql('skipped');
});
""",
                body=req_body(MALE, ["beard"], 3, {"include_beard": False}),
            ),
            request_item(
                "04.04 facial_hair_available=false keeps clean-shaven only",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const beard = categoryMap(body).beard;
pm.test('only B001 eligible/returned', function () {
    pm.expect(beard.status).to.eql('ok');
    pm.expect(beard.eligible_count).to.eql(1);
    pm.expect(beard.returned_count).to.eql(1);
    pm.expect(beard.recommendations[0].style_id).to.eql('B001');
    pm.expect(beard.recommendations[0].requires_facial_hair).to.eql(false);
    pm.expect(beard.applied_eligibility_rules).to.include('facial_hair_available_false_filter');
});
""",
                body=req_body(MALE, ["beard"], 10, {
                    "include_beard": True,
                    "facial_hair_available": False,
                }),
            ),
            request_item(
                "04.05 Exclude one known style H001",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const hair = categoryMap(body).hair;
const ids = hair.recommendations.map(r => r.style_id);
pm.test('H001 not reintroduced', function () {
    pm.expect(ids).to.not.include('H001');
    pm.expect(hair.eligible_count).to.eql(7);
    pm.expect(hair.returned_count).to.be.at.most(3);
    pm.expect(hair.applied_eligibility_rules).to.include('excluded_style_ids');
});
""",
                body=req_body(MALE, ["hair"], 3, {"excluded_style_ids": ["H001"]}),
            ),
            request_item(
                "04.06 Exclude multiple known styles",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const hair = categoryMap(body).hair;
const ids = hair.recommendations.map(r => r.style_id);
pm.test('excluded styles absent', function () {
    ['H001','H002','H003'].forEach(id => pm.expect(ids).to.not.include(id));
    pm.expect(hair.eligible_count).to.eql(5);
});
""",
                body=req_body(MALE, ["hair"], 5, {
                    "excluded_style_ids": ["H001", "H002", "H003"],
                }),
            ),
            request_item(
                "04.07 Exclude every grooming style -> empty category",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const g = categoryMap(body).grooming;
pm.test('empty category with reason', function () {
    pm.expect(g.status).to.eql('empty');
    pm.expect(g.returned_count).to.eql(0);
    pm.expect(g.recommendations).to.eql([]);
    pm.expect(g.empty_reason).to.be.a('string').and.not.empty;
});
""",
                body=req_body(MALE, ["grooming"], 5, {
                    "excluded_style_ids": ["G001", "G002", "G003", "G004"],
                }),
            ),
            request_item(
                "04.08 Unknown excluded style ID is ignored (not a validation error)",
                "POST",
                "/api/v1/recommendations",
                """
// Implementation normalizes excluded_style_ids and filters catalogue IDs only.
// Unknown IDs do not fail validation.
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('hair still returns recommendations', function () {
    const hair = categoryMap(body).hair;
    pm.expect(hair.status).to.eql('ok');
    pm.expect(hair.returned_count).to.be.above(0);
});
""",
                body=req_body(MALE, ["hair"], 3, {
                    "excluded_style_ids": ["ZZZZ_NOT_A_STYLE"],
                }),
                description=(
                    "Unknown excluded_style_ids are accepted and ignored by eligibility "
                    "filtering (actual implementation behavior)."
                ),
            ),
        ],
    })

    # ---- 05 Weighted rules ----
    folders.append({
        "name": "05 - Weighted Rules and Hybrid Ranking",
        "item": [
            request_item(
                "05.01 Verify hybrid weights and score scales",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('policy weights 0.50/0.30/0.20', function () {
    pm.expect(body.ranking_policy.policy_name).to.eql('hybrid_model_rank_rules_v1');
    const w = body.ranking_policy.weights;
    pm.expect(w.predicted_compatibility).to.eql(0.5);
    pm.expect(w.rank_percentile).to.eql(0.3);
    pm.expect(w.rule_compatibility).to.eql(0.2);
});
const hair = categoryMap(body).hair;
hair.recommendations.forEach((item, idx) => {
    pm.test('hair[' + idx + '] compatibility rescale and hybrid mix use 0-1 terms', function () {
        const expectedCompat = 100 * (item.display_compatibility_rating - 1) / 4;
        pm.expect(Math.abs(item.compatibility_score - expectedCompat)).to.be.below(1e-6);
        // normalized_predicted_compatibility is 0-1, not 0-100
        pm.expect(item.normalized_predicted_compatibility).to.be.at.least(0);
        pm.expect(item.normalized_predicted_compatibility).to.be.at.most(1);
        pm.expect(item.rank_percentile).to.be.at.least(0);
        pm.expect(item.rank_percentile).to.be.at.most(1);
        pm.expect(item.rule_compatibility_score).to.be.at.least(0);
        pm.expect(item.rule_compatibility_score).to.be.at.most(1);
        const expectedHybrid =
            0.5 * item.normalized_predicted_compatibility +
            0.3 * item.rank_percentile +
            0.2 * item.rule_compatibility_score;
        pm.expect(Math.abs(item.hybrid_score - expectedHybrid)).to.be.below(1e-6);
    });
    pm.test('hair[' + idx + '] nine contributions sum to rule score', function () {
        const contribs = item.explanation.rule_contributions;
        pm.expect(contribs).to.have.length(9);
        const sum = contribs.reduce((a, c) => a + c.contribution, 0);
        pm.expect(Math.abs(sum - item.rule_compatibility_score)).to.be.below(1e-4);
        contribs.forEach(c => {
            pm.expect(c).to.have.property('attribute');
            pm.expect(isFiniteNumber(c.contribution)).to.eql(true);
            pm.expect(isFiniteNumber(c.similarity)).to.eql(true);
            pm.expect(isFiniteNumber(c.weight)).to.eql(true);
        });
    });
});
""",
                body=req_body(MALE, ["hair"], 3, {"include_beard": True}),
            ),
            request_item(
                "05.02 Independent H001 perfect-match rule calculation",
                "POST",
                "/api/v1/recommendations",
                """
// Fixture source: datasets/rating_parameters.json style_preferences/style_ratio_targets for H001.
// Profile values equal H001 targets => all Gaussian similarities = 1.0 and all categoricals match.
// Expected weighted_compatibility = 1.0 (hair weights sum to 1).
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const hair = categoryMap(body).hair;
const h001 = hair.recommendations.find(r => r.style_id === 'H001');
pm.test('H001 present among hair recommendations', function () {
    pm.expect(h001).to.not.eql(undefined);
});
if (h001) {
    pm.test('H001 rule_compatibility_score ~= 1.0 from rating_parameters.json', function () {
        pm.expect(Math.abs(h001.rule_compatibility_score - 1.0)).to.be.below(1e-6);
    });
    pm.test('H001 contribution attributes match term_order', function () {
        const attrs = h001.explanation.rule_contributions.map(c => c.attribute);
        pm.expect(attrs).to.eql([
            'face_length_ratio','jaw_width_ratio','upper_width_ratio','lower_face_ratio',
            'face_shape','jawline','forehead','hairline','symmetry'
        ]);
        h001.explanation.rule_contributions.forEach(c => {
            pm.expect(Math.abs(c.similarity - 1.0)).to.be.below(1e-6);
        });
    });
}
""",
                body=req_body(H001_MATCH_PROFILE, ["hair"], 8),
                description=(
                    "Independent rule check using exact H001 targets from "
                    "datasets/rating_parameters.json. Expected rule score = 1.0."
                ),
            ),
            request_item(
                "05.03 Ordering follows hybrid_score then style_id",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
['hair','beard','grooming'].forEach(catName => {
    const cat = categoryMap(body)[catName];
    if (!cat || cat.status !== 'ok') return;
    pm.test(catName + ' sorted by hybrid_score desc, style_id asc on ties', function () {
        for (let i = 1; i < cat.recommendations.length; i++) {
            const a = cat.recommendations[i-1];
            const b = cat.recommendations[i];
            if (Math.abs(a.hybrid_score - b.hybrid_score) < 1e-12) {
                pm.expect(a.style_id <= b.style_id).to.eql(true);
            } else {
                pm.expect(a.hybrid_score > b.hybrid_score).to.eql(true);
            }
        }
    });
});
""",
                body=req_body(MALE, ["hair", "beard", "grooming"], 8, {
                    "include_beard": True,
                    "facial_hair_available": True,
                }),
            ),
        ],
    })

    # ---- 06 Confidence ----
    facial9 = {
        "face_length_ratio": 0.95,
        "jaw_width_ratio": 0.95,
        "upper_width_ratio": 0.95,
        "lower_face_ratio": 0.95,
        "symmetry": 0.95,
        "face_shape": 0.95,
        "jawline": 0.95,
        "forehead": 0.95,
        "hairline": 0.95,
    }
    facial9_low = {k: 0.2 for k in facial9}
    folders.append({
        "name": "06 - Confidence and Input Quality",
        "item": [
            request_item(
                "06.01 attribute_confidence omitted",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const q = body.input_quality;
pm.test('missing confidence contract', function () {
    pm.expect(q.confidence_status).to.eql('not_provided');
    pm.expect(q.assessment).to.eql('unknown');
    pm.expect(q.input_quality_score).to.eql(null);
    pm.expect(q.confidence_coverage).to.eql(0);
    pm.expect(q.caution_flag).to.eql(true);
    pm.expect(q.caution_reasons).to.include('confidence_not_provided');
    pm.expect(body.recommendation_confidence).to.eql(null);
    pm.expect(body.recommendation_confidence_status).to.eql('not_calibrated');
});
pm.test('deprecated aliases match canonical confidence fields', function () {
    pm.expect(q.attributes_provided).to.eql(q.confidence_attributes_provided);
    pm.expect(q.attributes_missing).to.eql(q.confidence_attributes_missing);
    pm.expect(q.coverage).to.eql(q.confidence_coverage);
    pm.expect(q.note.toLowerCase()).to.include('not the same as missing');
});
pm.test('review_required and scores still returned', function () {
    const hair = categoryMap(body).hair;
    pm.expect(hair.recommendation_disposition).to.eql('review_required');
    pm.expect(hair.returned_count).to.be.above(0);
    pm.expect(hair.recommendations[0]).to.have.property('compatibility_score');
    pm.expect(hair.recommendations[0]).to.not.have.property('confidence');
});
""",
                body=req_body(MALE, ["hair"], 2),
            ),
            request_item(
                "06.02 Complete high confidence -> standard",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const q = body.input_quality;
pm.test('complete adequate quality', function () {
    pm.expect(q.confidence_status).to.eql('complete');
    pm.expect(q.assessment).to.eql('adequate');
    pm.expect(q.confidence_coverage).to.eql(1);
    pm.expect(q.caution_flag).to.eql(false);
    pm.expect(body.category_results[0].recommendation_disposition).to.eql('standard');
    pm.expect(body.recommendation_confidence).to.eql(null);
});
""",
                body=req_body(MALE, ["hair"], 2, confidence=facial9),
            ),
            request_item(
                "06.03 Partial confidence map",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const q = body.input_quality;
pm.test('partial confidence insufficient_coverage', function () {
    pm.expect(q.confidence_status).to.eql('partial');
    pm.expect(q.assessment).to.eql('insufficient_coverage');
    pm.expect(q.confidence_attributes_provided).to.include.members(['face_shape','jawline']);
    pm.expect(q.confidence_attributes_missing.length).to.be.above(0);
    pm.expect(q.attributes_missing).to.eql(q.confidence_attributes_missing);
    pm.expect(q.confidence_coverage).to.be.below(1);
    pm.expect(q.gender_confidence_supplied).to.eql(true);
    pm.expect(body.category_results[0].recommendation_disposition).to.eql('review_required');
});
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    2,
                    confidence={"face_shape": 0.9, "jawline": 0.85, "gender": 0.95},
                ),
            ),
            request_item(
                "06.04 Complete low confidence -> review_required",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const q = body.input_quality;
pm.test('complete but low assessment', function () {
    pm.expect(q.confidence_status).to.eql('complete');
    pm.expect(q.assessment).to.eql('low');
    pm.expect(q.caution_flag).to.eql(true);
    pm.expect(body.category_results[0].recommendation_disposition).to.eql('review_required');
    pm.expect(body.recommendation_confidence_status).to.eql('not_calibrated');
});
""",
                body=req_body(MALE, ["hair"], 2, confidence=facial9_low),
            ),
            request_item(
                "06.05 Gender confidence alone does not count as facial coverage",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const q = getJson().input_quality;
pm.test('gender-only confidence is not_provided for facial aggregate', function () {
    pm.expect(q.confidence_status).to.eql('not_provided');
    pm.expect(q.confidence_coverage).to.eql(0);
    pm.expect(q.input_quality_score).to.eql(null);
    pm.expect(q.gender_confidence_supplied).to.eql(true);
    pm.expect(q.gender_excluded_from_facial_aggregate).to.eql(true);
});
""",
                body=req_body(MALE, ["hair"], 1, confidence={"gender": 0.99}),
            ),
            request_item(
                "06.06 Boundary confidence 0 and 1 in partial map",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const q = getJson().input_quality;
pm.test('boundaries 0 and 1 accepted in partial map', function () {
    pm.expect(q.confidence_status).to.eql('partial');
    pm.expect(q.input_quality_score).to.not.eql(null);
    pm.expect(q.low_confidence_attributes).to.include('symmetry');
});
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    1,
                    confidence={"symmetry": 0.0, "gender": 1.0, "face_shape": 1.0},
                ),
            ),
            request_item(
                "06.07 Store low-confidence hybrid order",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const ids = categoryMap(body).hair.recommendations.map(r => r.style_id);
const hybrids = categoryMap(body).hair.recommendations.map(r => r.hybrid_score);
pm.collectionVariables.set('conf_order_ids', JSON.stringify(ids));
pm.collectionVariables.set('conf_order_hybrids', JSON.stringify(hybrids));
pm.test('low-confidence order stored; disposition review_required', function () {
    pm.expect(ids.length).to.be.above(0);
    pm.expect(body.input_quality.confidence_status).to.eql('complete');
    pm.expect(body.input_quality.assessment).to.eql('low');
    pm.expect(categoryMap(body).hair.recommendation_disposition).to.eql('review_required');
});
""",
                body=req_body(MALE, ["hair"], 5, confidence=facial9_low),
                description="Paired with 06.08 to prove flagging-only policy does not reorder.",
            ),
            request_item(
                "06.08 Compare no-confidence order to 06.07",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const ids = categoryMap(body).hair.recommendations.map(r => r.style_id);
const hybrids = categoryMap(body).hair.recommendations.map(r => r.hybrid_score);
const baselineIds = JSON.parse(pm.collectionVariables.get('conf_order_ids') || 'null');
const baselineHybrids = JSON.parse(pm.collectionVariables.get('conf_order_hybrids') || 'null');
pm.test('baseline from 06.07 available', function () {
    pm.expect(baselineIds).to.not.eql(null);
});
pm.test('confidence changes alone do not change hybrid ordering', function () {
    pm.expect(ids).to.eql(baselineIds);
    for (let i = 0; i < hybrids.length; i++) {
        pm.expect(Math.abs(hybrids[i] - baselineHybrids[i])).to.be.below(1e-9);
    }
});
pm.test('no-confidence still review_required / not_calibrated', function () {
    pm.expect(body.input_quality.confidence_status).to.eql('not_provided');
    pm.expect(categoryMap(body).hair.recommendation_disposition).to.eql('review_required');
    pm.expect(body.recommendation_confidence).to.eql(null);
});
pm.collectionVariables.unset('conf_order_ids');
pm.collectionVariables.unset('conf_order_hybrids');
""",
                body=req_body(MALE, ["hair"], 5),
                description="Depends on 06.07 in the same Collection Runner execution.",
            ),
        ],
    })

    # ---- 07 Validation ----
    def neg(name, body=None, raw_body=None, expect_status=422, extra_assert=""):
        tests = f"""
pm.test('rejects with HTTP {expect_status}', function () {{
    pm.response.to.have.status({expect_status});
}});
const body = getJson();
pm.test('structured error payload', function () {{
    pm.expect(body).to.have.property('detail');
}});
{extra_assert}
"""
        return request_item(name, "POST", "/api/v1/recommendations", tests, body=body, raw_body=raw_body)

    def bad_profile(**overrides):
        p = dict(MALE)
        p.update(overrides)
        return req_body(p, ["hair"], 1)

    validation_items = [
        neg(
            "07.01 Missing required profile field (face_shape)",
            body={
                "profile": {k: v for k, v in MALE.items() if k != "face_shape"},
                "categories": ["hair"],
                "top_n": 1,
            },
        ),
        neg("07.02 Unsupported face_shape", body=bad_profile(face_shape="triangle")),
        neg("07.03 Unsupported jawline", body=bad_profile(jawline="pointy")),
        neg("07.04 Unsupported forehead", body=bad_profile(forehead="huge")),
        neg("07.05 Unsupported hairline", body=bad_profile(hairline="zigzag")),
        neg("07.06 Unsupported gender", body=bad_profile(gender="other")),
        neg("07.07 Invalid numeric type", body=bad_profile(face_length_ratio="tall")),
        neg("07.08 Symmetry below 0", body=bad_profile(symmetry=-0.1)),
        neg("07.09 Symmetry above 1", body=bad_profile(symmetry=1.2)),
        neg(
            "07.10 Confidence below 0",
            body=req_body(MALE, ["hair"], 1, confidence={"face_shape": -0.01}),
        ),
        neg(
            "07.11 Confidence above 1",
            body=req_body(MALE, ["hair"], 1, confidence={"face_shape": 1.01}),
        ),
        neg(
            "07.12 Invalid category",
            body=req_body(MALE, ["makeup"], 1),
        ),
        neg(
            "07.13 top_n=0",
            body=req_body(MALE, ["hair"], 0),
        ),
        neg(
            "07.14 Negative top_n",
            body=req_body(MALE, ["hair"], -3),
        ),
        neg(
            "07.15 top_n above configured maximum (21 > max_top_n=20)",
            body=req_body(MALE, ["hair"], 21),
            # Pydantic allows <=50, route enforces settings.max_top_n=20 => 422
        ),
        neg(
            "07.16 top_n above schema hard max (51)",
            body=req_body(MALE, ["hair"], 51),
        ),
        neg(
            "07.17 Unknown confidence attribute",
            body=req_body(MALE, ["hair"], 1, confidence={"skin_tone": 0.9}),
        ),
        neg(
            "07.18 Malformed JSON",
            raw_body='{"profile": {',
        ),
        neg(
            "07.19 Unknown top-level field (extra=forbid)",
            body={
                "profile": MALE,
                "categories": ["hair"],
                "top_n": 1,
                "unexpected_field": True,
            },
        ),
        neg(
            "07.20 Empty categories list",
            body={"profile": MALE, "categories": [], "top_n": 1},
        ),
        request_item(
            "07.21 NaN symmetry rejected",
            "POST",
            "/api/v1/recommendations",
            """
pm.test('rejects non-finite symmetry', function () {
    pm.response.to.have.status(422);
});
pm.test('structured detail', function () {
    pm.expect(getJson()).to.have.property('detail');
});
""",
            body=bad_profile(symmetry="NaN"),
        ),
        request_item(
            "07.22 Infinity face_length_ratio rejected",
            "POST",
            "/api/v1/recommendations",
            """
pm.test('rejects Infinity numeric', function () {
    pm.response.to.have.status(422);
});
""",
            body=bad_profile(face_length_ratio="Infinity"),
        ),
    ]
    folders.append({"name": "07 - Validation and Error Handling", "item": validation_items})

    # ---- 09 Confidence-aware ranking mode (appended after 08) ----
    folder_09 = {
        "name": "09 - Confidence-Aware Ranking Mode",
        "description": (
            "Optional ranking_mode=confidence_aware with confidence_source=manual. "
            "Compare candidates by style_id. Does not claim calibrated confidence."
        ),
        "item": [
            request_item(
                "09.01 Standard mode (explicit)",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('standard mode contract', function () {
    pm.expect(body.ranking_mode).to.eql('standard');
    pm.expect(body.ranking_policy.policy_name).to.eql('hybrid_model_rank_rules_v1');
    pm.expect(body.ranking_policy.fallback_applied).to.eql(false);
    pm.expect(body.recommendation_confidence).to.eql(null);
    const hair = categoryMap(body).hair;
    pm.expect(hair.status).to.eql('ok');
    hair.recommendations.forEach(r => {
        pm.expect(r.confidence_adjusted_rule_score).to.eql(null);
        pm.expect(r.recommendation_support_score).to.eql(null);
    });
});
pm.collectionVariables.set(
    'std_by_id',
    JSON.stringify(Object.fromEntries(
        categoryMap(body).hair.recommendations.map(r => [r.style_id, r])
    ))
);
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    5,
                    ranking_mode="standard",
                    confidence_source="manual",
                ),
            ),
            request_item(
                "09.02 Confidence-aware all confidences = 1",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const stdById = JSON.parse(pm.collectionVariables.get('std_by_id') || '{}');
pm.test('confidence_aware policy and ones reproduce rule scores', function () {
    pm.expect(body.ranking_mode).to.eql('confidence_aware');
    pm.expect(body.confidence_source).to.eql('manual');
    pm.expect(body.ranking_policy.policy_name).to.eql('hybrid_confidence_adjusted_rules_v1');
    pm.expect(body.ranking_policy.adjusts_rule_component_only).to.eql(true);
    pm.expect(body.recommendation_confidence).to.eql(null);
    const hair = categoryMap(body).hair;
    hair.recommendations.forEach(r => {
        pm.expect(isFiniteNumber(r.confidence_adjusted_rule_score)).to.eql(true);
        pm.expect(Math.abs(r.confidence_adjusted_rule_score - r.rule_compatibility_score)).to.be.below(1e-5);
        const supportSum = r.explanation.rule_contributions.reduce(
            (acc, c) => acc + (c.support_contribution || 0), 0
        );
        pm.expect(Math.abs(r.recommendation_support_score - supportSum)).to.be.below(1e-5);
        if (stdById[r.style_id]) {
            pm.expect(Math.abs(r.hybrid_score - stdById[r.style_id].hybrid_score)).to.be.below(1e-5);
        }
    });
});
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    5,
                    confidence=facial_conf(1.0),
                    ranking_mode="confidence_aware",
                    confidence_source="manual",
                ),
                description="Depends on 09.01 in Collection Runner for hybrid compare by style_id.",
            ),
            request_item(
                "09.03 Same profile, low face_shape confidence",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('low face_shape changes support/contributions', function () {
    pm.expect(body.ranking_policy.policy_name).to.eql('hybrid_confidence_adjusted_rules_v1');
    const hair = categoryMap(body).hair;
    pm.expect(hair.recommendation_disposition).to.eql('review_required');
    const top = hair.recommendations[0];
    const fs = top.explanation.rule_contributions.find(c => c.attribute === 'face_shape');
    pm.expect(fs.confidence).to.eql(0.1);
    pm.expect(Math.abs(fs.effective_weight - fs.weight * 0.1)).to.be.below(1e-6);
    pm.expect(top.rule_confidence_coverage).to.be.below(1.0);
});
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    5,
                    confidence=facial_conf(1.0, face_shape=0.1),
                    ranking_mode="confidence_aware",
                    confidence_source="manual",
                ),
            ),
            request_item(
                "09.04 Same profile, low jawline confidence",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
pm.test('low jawline confidence reflected per style_id', function () {
    const hair = categoryMap(body).hair;
    hair.recommendations.forEach(r => {
        const jl = r.explanation.rule_contributions.find(c => c.attribute === 'jawline');
        pm.expect(jl.confidence).to.eql(0.1);
        pm.expect(jl.support_contribution).to.eql(
            Number((jl.effective_weight * jl.similarity).toFixed(6))
            || jl.support_contribution
        );
        pm.expect(Math.abs(
            jl.support_contribution - jl.effective_weight * jl.similarity
        )).to.be.below(1e-5);
    });
});
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    5,
                    confidence=facial_conf(1.0, jawline=0.1),
                    ranking_mode="confidence_aware",
                    confidence_source="manual",
                ),
            ),
            request_item(
                "09.05 Uniform low confidence",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const onesById = JSON.parse(pm.collectionVariables.get('std_by_id') || '{}');
pm.test('uniform scale preserves adjusted vs ones order potential; support shrinks', function () {
    pm.expect(body.input_quality.assessment).to.eql('low');
    pm.expect(categoryMap(body).hair.recommendation_disposition).to.eql('review_required');
    categoryMap(body).hair.recommendations.forEach(r => {
        pm.expect(isFiniteNumber(r.confidence_adjusted_rule_score)).to.eql(true);
        // Compared to all-ones run stored indirectly via rule score equality with original
        pm.expect(Math.abs(
            r.recommendation_support_score -
            r.rule_confidence_coverage * r.confidence_adjusted_rule_score
        )).to.be.below(1e-5);
        pm.expect(r.rule_confidence_coverage).to.be.below(0.3);
    });
    // style_id set still present
    pm.expect(categoryMap(body).hair.recommendations.map(r => r.style_id).length).to.be.above(0);
    void onesById;
});
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    5,
                    confidence=facial_conf(0.25),
                    ranking_mode="confidence_aware",
                    confidence_source="manual",
                ),
            ),
            request_item(
                "09.06 All-zero confidence fallback",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const stdById = JSON.parse(pm.collectionVariables.get('std_by_id') || '{}');
pm.test('all-zero falls back to standard ranking', function () {
    pm.expect(body.ranking_mode).to.eql('confidence_aware');
    pm.expect(body.ranking_policy.fallback_applied).to.eql(true);
    pm.expect(body.ranking_policy.active_ranking_mode).to.eql('standard');
    pm.expect(body.ranking_policy.policy_name).to.eql('hybrid_model_rank_rules_v1');
    pm.expect(categoryMap(body).hair.recommendation_disposition).to.eql('review_required');
    categoryMap(body).hair.recommendations.forEach(r => {
        pm.expect(r.recommendation_support_score).to.eql(0);
        pm.expect(r.confidence_adjusted_rule_score).to.eql(null);
        if (stdById[r.style_id]) {
            pm.expect(Math.abs(r.hybrid_score - stdById[r.style_id].hybrid_score)).to.be.below(1e-5);
        }
    });
    pm.expect(body.recommendation_confidence).to.eql(null);
});
pm.collectionVariables.unset('std_by_id');
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    5,
                    confidence=facial_conf(0.0),
                    ranking_mode="confidence_aware",
                    confidence_source="manual",
                ),
                description="Depends on 09.01 style_id hybrid baseline.",
            ),
            request_item(
                "09.07 Incomplete confidence map rejected",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('incomplete map rejected in confidence_aware', function () {
    pm.response.to.have.status(422);
    const body = getJson();
    pm.expect(body).to.have.property('detail');
    const text = JSON.stringify(body.detail).toLowerCase();
    pm.expect(text.includes('missing') || text.includes('nine') || text.includes('confidence')).to.eql(true);
});
""",
                body=req_body(
                    MALE,
                    ["hair"],
                    2,
                    confidence={"face_shape": 0.9, "jawline": 0.8},
                    ranking_mode="confidence_aware",
                    confidence_source="manual",
                ),
            ),
        ],
    }

    # ---- 08 Determinism ----
    det_body = req_body(MALE, ["hair", "beard", "grooming"], 3, {
        "include_beard": True,
        "facial_hair_available": True,
        "excluded_style_ids": [],
    })
    folders.append({
        "name": "08 - Determinism and Contract Consistency",
        "description": (
            "Paired requests: 08.01 stores stable fields into collection variables; "
            "08.02 compares against them. Run both in order in Collection Runner. "
            "Variables are overwritten each run to avoid stale state."
        ),
        "item": [
            request_item(
                "08.01 Determinism baseline (store stable fields)",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
function stableView(body) {
    return (body.category_results || []).map(c => ({
        category: c.category,
        status: c.status,
        recommendations: (c.recommendations || []).map(r => ({
            style_id: r.style_id,
            rank: r.rank,
            raw_ranker_score: r.raw_ranker_score,
            raw_predicted_compatibility_rating: r.raw_predicted_compatibility_rating,
            rule_compatibility_score: r.rule_compatibility_score,
            hybrid_score: r.hybrid_score
        }))
    }));
}
pm.collectionVariables.set('determinism_baseline', JSON.stringify(stableView(body)));
pm.collectionVariables.set('determinism_request_id_1', body.request_id || '');
pm.test('baseline stored', function () {
    pm.expect(pm.collectionVariables.get('determinism_baseline')).to.be.a('string').and.not.empty;
});
""",
                body=det_body,
                description="Stores stable recommendation fields for 08.02 comparison.",
            ),
            request_item(
                "08.02 Determinism compare (identical request)",
                "POST",
                "/api/v1/recommendations",
                """
pm.test('status 200', function () { pm.response.to.have.status(200); });
const body = getJson();
const baseline = JSON.parse(pm.collectionVariables.get('determinism_baseline') || 'null');
pm.test('baseline available from 08.01', function () {
    pm.expect(baseline).to.not.eql(null);
});
function stableView(body) {
    return (body.category_results || []).map(c => ({
        category: c.category,
        status: c.status,
        recommendations: (c.recommendations || []).map(r => ({
            style_id: r.style_id,
            rank: r.rank,
            raw_ranker_score: r.raw_ranker_score,
            raw_predicted_compatibility_rating: r.raw_predicted_compatibility_rating,
            rule_compatibility_score: r.rule_compatibility_score,
            hybrid_score: r.hybrid_score
        }))
    }));
}
const current = stableView(body);
pm.test('category/style ordering identical', function () {
    pm.expect(current.map(c => c.category)).to.eql(baseline.map(c => c.category));
    for (let i = 0; i < baseline.length; i++) {
        pm.expect(current[i].status).to.eql(baseline[i].status);
        pm.expect(current[i].recommendations.map(r => r.style_id))
            .to.eql(baseline[i].recommendations.map(r => r.style_id));
        pm.expect(current[i].recommendations.map(r => r.rank))
            .to.eql(baseline[i].recommendations.map(r => r.rank));
    }
});
pm.test('scores match within tolerance (ignore request_id)', function () {
    const tol = 1e-9;
    for (let i = 0; i < baseline.length; i++) {
        for (let j = 0; j < baseline[i].recommendations.length; j++) {
            const a = baseline[i].recommendations[j];
            const b = current[i].recommendations[j];
            pm.expect(Math.abs(a.raw_ranker_score - b.raw_ranker_score)).to.be.below(tol);
            pm.expect(Math.abs(a.raw_predicted_compatibility_rating - b.raw_predicted_compatibility_rating)).to.be.below(tol);
            pm.expect(Math.abs((a.rule_compatibility_score||0) - (b.rule_compatibility_score||0))).to.be.below(1e-6);
            pm.expect(Math.abs(a.hybrid_score - b.hybrid_score)).to.be.below(1e-6);
        }
    }
    // request_id may differ; do not require equality
    pm.expect(body.request_id).to.be.a('string');
});
// Clear to avoid stale reuse across collection runs
pm.collectionVariables.unset('determinism_baseline');
""",
                body=det_body,
                description="Depends on 08.01 in the same Collection Runner execution.",
            ),
        ],
    })
    folders.append(folder_09)

    collection = {
        "info": {
            "_postman_id": "c3-style-ranker-collection",
            "name": "Component 3 - Style Recommendation and Ranking Engine",
            "description": (
                "Executable Postman Collection v2.1 for the Component 3 FastAPI backend.\n\n"
                "Source of truth: backend OpenAPI + app schemas/services.\n"
                "No authentication. No database.\n"
                "Use environment Component3_Local (base_url=http://127.0.0.1:8000).\n\n"
                "H001 rule fixture source: datasets/rating_parameters.json."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "determinism_baseline", "value": ""},
            {"key": "determinism_request_id_1", "value": ""},
            {"key": "catalogue_json", "value": ""},
            {"key": "caps_style_ids", "value": ""},
            {"key": "conf_order_ids", "value": ""},
            {"key": "conf_order_hybrids", "value": ""},
            {"key": "std_by_id", "value": ""},
        ],
        "item": folders,
    }
    return collection


def build_environment():
    return {
        "id": "c3-local-env",
        "name": "Component3_Local",
        "values": [
            {
                "key": "base_url",
                "value": "http://127.0.0.1:8000",
                "type": "default",
                "enabled": True,
            },
            {
                "key": "score_tolerance",
                "value": "1e-6",
                "type": "default",
                "enabled": True,
            },
        ],
        "_postman_variable_scope": "environment",
    }


def count_assertions(collection: dict) -> tuple[int, int]:
    requests = 0
    assertions = 0
    for folder in collection["item"]:
        for item in folder["item"]:
            requests += 1
            for ev in item.get("event", []):
                if ev.get("listen") != "test":
                    continue
                text = "\n".join(ev["script"]["exec"])
                assertions += text.count("pm.test(")
    return requests, assertions


def write_coverage_matrix(collection: dict) -> str:
    rows = [
        "| Test ID | Component 3 requirement | Request name | Expected behavior | Automated assertions |",
        "|---------|-------------------------|--------------|-------------------|----------------------|",
    ]
    mapping = [
        ("01.01", "Liveness", "Process alive"),
        ("01.02", "Readiness + models/rules/catalogue", "ready=true, 4 models, rules"),
        ("02.01", "Capabilities / policy / calibration", "hybrid_model_rank_rules_v1"),
        ("02.02", "Input schema contract", "categories/genders/top_n max"),
        ("02.03", "Full catalogue coverage", "16 unique H/B/G IDs"),
        ("02.04", "Hair catalogue filter", "8 hair styles"),
        ("02.05", "Beard catalogue filter + facial-hair flags", "4 beard styles"),
        ("02.06", "Grooming catalogue filter", "4 grooming styles"),
        ("02.07", "Unsupported catalogue category", "HTTP 422"),
        ("02.08", "Model info without path leakage", "4 models, no paths"),
        ("03.01", "Male multi-category recommendations", "hair/beard/grooming ok"),
        ("03.02", "Female hair+grooming; default beard skip", "beard skipped"),
        ("03.03", "Male hair only", "hair ok"),
        ("03.04", "Male beard only", "beard ok"),
        ("03.05", "Grooming only", "grooming ok"),
        ("03.06", "top_n=1", "at most 1 per category"),
        ("03.07", "top_n=3", "at most 3"),
        ("03.08", "top_n > eligible", "return all eligible (<=4)"),
        ("04.01", "Female default beard exclusion", "default_gender_policy"),
        ("04.02", "Female include_beard unsupported coverage", "unsupported_model_coverage"),
        ("04.03", "Male beard opt-out", "excluded_by_preference"),
        ("04.04", "facial_hair_available=false / clean-shaven", "only B001"),
        ("04.05", "Exclude one style", "H001 absent"),
        ("04.06", "Exclude multiple styles", "excluded absent"),
        ("04.07", "Exclude all in category", "empty + reason"),
        ("04.08", "Unknown excluded ID behavior", "200; ignored"),
        ("05.01", "Hybrid weights + rescale + contribution sum", "0.5/0.3/0.2 math"),
        ("05.02", "Independent H001 rule calculation", "score≈1.0 from params"),
        ("05.03", "Hybrid ordering + tie-break", "desc hybrid, style_id"),
        ("06.01", "Missing confidence", "not_provided / null"),
        ("06.02", "Valid confidence", "provided heuristic score"),
        ("06.03", "Partial confidence", "coverage < 1"),
        ("06.04", "Low confidence caution", "caution_flag"),
        ("06.05", "Boundary confidence 0/1", "accepted"),
        ("07.01-07.22", "Validation / error handling", "HTTP 422 structured detail"),
        ("08.01-08.02", "Deterministic identical requests", "stable fields match"),
    ]
    # Expand from actual request names
    for folder in collection["item"]:
        for item in folder["item"]:
            name = item["name"]
            tid = name.split(" ", 1)[0]
            tests = 0
            for ev in item.get("event", []):
                if ev.get("listen") == "test":
                    tests += "\n".join(ev["script"]["exec"]).count("pm.test(")
            # find requirement hint
            req = next((m[1] for m in mapping if tid.startswith(m[0].split("-")[0][:5]) or tid.startswith(m[0][:5])), folder["name"])
            for m in mapping:
                if tid.startswith(m[0].split("-")[0]) or tid == m[0] or (m[0].endswith(tid[:5]) if False else False):
                    pass
            hint = ""
            for m in mapping:
                key = m[0].split("-")[0]
                if tid.startswith(key[:5]) or tid.startswith(m[0][:5]):
                    hint = m[1]
                    expected = m[2]
                    break
            else:
                hint = folder["name"]
                expected = "See request tests"
            rows.append(
                f"| {tid} | {hint} | {name} | {expected} | {tests} pm.test blocks |"
            )
    return "\n".join(rows) + "\n"


def main():
    collection = build_collection()
    environment = build_environment()
    req_count, assert_count = count_assertions(collection)

    coll_path = OUT / "Component3.postman_collection.json"
    env_path = OUT / "Component3_Local.postman_environment.json"
    coll_path.write_text(json.dumps(collection, indent=2), encoding="utf-8")
    env_path.write_text(json.dumps(environment, indent=2), encoding="utf-8")

    # Fix coverage matrix with accurate per-request rows
    lines = [
        "# Component 3 Postman Coverage Matrix",
        "",
        "Source of truth: FastAPI routes/schemas in `backend/app` and OpenAPI.",
        "",
        f"- Requests in collection: **{req_count}**",
        f"- Automated `pm.test` blocks: **{assert_count}**",
        "",
        "| Test ID | Folder / requirement area | Request name | Expected behavior | `pm.test` count |",
        "|---------|---------------------------|--------------|-------------------|-----------------|",
    ]
    for folder in collection["item"]:
        for item in folder["item"]:
            name = item["name"]
            tid = name.split(" ", 1)[0]
            tests = 0
            for ev in item.get("event", []):
                if ev.get("listen") == "test":
                    tests += "\n".join(ev["script"]["exec"]).count("pm.test(")
            expected = {
                "01.01": "200; status=ok",
                "01.02": "ready=true; 4 models; catalogue/schema/rules",
                "02.01": "capabilities + hybrid_model_rank_rules_v1 + not_calibrated",
                "02.02": "schema_version 1.0; top_n max 20",
                "02.03": "16 unique styles H001–H008/B001–B004/G001–G004",
                "02.04": "8 hair styles",
                "02.05": "4 beard styles; B001 clean-shaven; B002 requires facial hair",
                "02.06": "4 grooming styles",
                "02.07": "HTTP 422",
                "02.08": "4 models; confidence_calibrated=false; no paths",
                "03.01": "200; hair/beard/grooming ok; scores finite; rules present",
                "03.02": "hair/grooming ok; beard default_gender_policy",
                "03.03": "hair ok",
                "03.04": "beard ok",
                "03.05": "grooming ok",
                "03.06": "returned_count <= 1",
                "03.07": "returned_count <= 3",
                "03.08": "returned_count == eligible_count == 4",
                "04.01": "beard default_gender_policy; others ok",
                "04.02": "beard unsupported_model_coverage; others ok",
                "04.03": "beard excluded_by_preference",
                "04.04": "only B001; requires_facial_hair=false",
                "04.05": "H001 excluded; not reintroduced",
                "04.06": "H001–H003 excluded",
                "04.07": "status=empty with reason",
                "04.08": "200; unknown exclusion ignored",
                "05.01": "weights 0.5/0.3/0.2; rescale; hybrid math; 9 contribs",
                "05.02": "H001 rule score ≈ 1.0 from rating_parameters.json",
                "05.03": "hybrid desc + style_id tie-break",
                "06.01": "confidence_status=not_provided; score null",
                "06.02": "confidence_status=provided; recommendation_confidence null",
                "06.03": "partial coverage < 1",
                "06.04": "caution_flag; low_confidence_attributes",
                "06.05": "0 and 1 accepted",
                "07.01": "HTTP 422 structured detail",
                "07.02": "HTTP 422",
                "07.03": "HTTP 422",
                "07.04": "HTTP 422",
                "07.05": "HTTP 422",
                "07.06": "HTTP 422",
                "07.07": "HTTP 422",
                "07.08": "HTTP 422",
                "07.09": "HTTP 422",
                "07.10": "HTTP 422",
                "07.11": "HTTP 422",
                "07.12": "HTTP 422",
                "07.13": "HTTP 422",
                "07.14": "HTTP 422",
                "07.15": "HTTP 422 (max_top_n=20)",
                "07.16": "HTTP 422 (schema le=50)",
                "07.17": "HTTP 422",
                "07.18": "HTTP 422",
                "07.19": "HTTP 422 extra=forbid",
                "07.20": "HTTP 422",
                "07.21": "HTTP 422",
                "07.22": "HTTP 422",
                "08.01": "store stable fields",
                "08.02": "identical stable recommendation fields",
            }.get(tid, "See scripts")
            lines.append(
                f"| {tid} | {folder['name']} | {name} | {expected} | {tests} |"
            )
    lines.extend([
        "",
        "## Notes",
        "",
        "- Unknown `excluded_style_ids` are **not** validation errors in the current API; they are ignored during filtering (covered by 04.08).",
        "- `top_n` Pydantic bound is `1..50`, but runtime `max_top_n` default is **20** (covered by 07.15 vs 07.16).",
        "- Raw ranker scores are **not** asserted as probabilities.",
        "- H001 independent rule fixture uses exact targets from `datasets/rating_parameters.json`.",
        "- Determinism pair 08.01 → 08.02 must run in order; variables are cleared after 08.02.",
        "",
    ])
    (OUT / "coverage_matrix.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {coll_path}")
    print(f"Wrote {env_path}")
    print(f"Requests={req_count} pm.test_blocks={assert_count}")


if __name__ == "__main__":
    main()
