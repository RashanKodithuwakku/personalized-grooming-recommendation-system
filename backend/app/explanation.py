"""Plain-language explanations based on supplied recommendation metadata."""


def generate_explanation(attribution_data):
    """Build a cautious explanation without inventing unsupported face traits.

    Expected optional keys:
      - contributing_factors: mapping of measured factors to similarity scores
      - match_score: geometric similarity in [0, 1]
      - confidence: upstream style-ranking confidence in [0, 1]
    """
    data = attribution_data or {}
    factors = data.get("contributing_factors") or {}
    valid_factors = {}
    for name, score in factors.items():
        try:
            value = float(score)
        except (TypeError, ValueError):
            continue
        if value == value and 0.0 <= value <= 1.0:
            valid_factors[str(name)] = value

    parts = []
    if valid_factors:
        top_factor = max(valid_factors, key=valid_factors.get)
        labels = {
            "face_width": "the face-width proportion measured from your photo",
            "hair_coverage": "the visible hair-coverage pattern measured from your photo",
            "geometry_match": "the measured face and hair geometry",
        }
        factor_label = labels.get(top_factor, top_factor.replace("_", " "))
        parts.append(f"This template was selected partly because it matches {factor_label}.")
    else:
        parts.append("This preview uses the closest available template variant based on the measured face and hair geometry.")

    match_score = data.get("match_score")
    try:
        match_score = float(match_score)
        if 0.0 <= match_score <= 1.0:
            parts.append(f"Geometry similarity score: {round(match_score * 100)}% (an internal matching score, not a guarantee of visual quality).")
    except (TypeError, ValueError):
        pass

    confidence = data.get("confidence")
    try:
        confidence = float(confidence)
        if 0.0 <= confidence <= 1.0:
            parts.append(f"Style-ranking confidence: {round(confidence * 100)}%.")
    except (TypeError, ValueError):
        pass

    return " ".join(parts)
