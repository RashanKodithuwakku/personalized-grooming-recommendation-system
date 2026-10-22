"""Composite weights: 0.50 shape, 0.25 symmetry, 0.25 balance.

No proportion term. A missing score is dropped and the rest renormalised.
"""

from pytest import approx

from face_shape.score.composite import score_composite, shape_confidence


# The shape term is the largest class confidence, here oval at 0.62.
def test_shape_confidence_is_the_winning_class():
    assert shape_confidence(
        {
            "oval": 0.62,
            "round": 0.18,
            "square": 0.08,
            "oblong": 0.06,
            "heart": 0.04,
            "diamond": 0.02,
        }
    ) == approx(0.62)


# With all three scores present the weights stay 0.50, 0.25, 0.25.
def test_full_weights_are_half_shape_quarter_symmetry_quarter_balance():
    result = score_composite(0.80, 0.60, 0.40)
    expected = 0.50 * 0.80 + 0.25 * 0.60 + 0.25 * 0.40
    assert result.compatibility_score == approx(expected)
    assert result.grooming_suitability_index == approx(round(100.0 * expected, 1))
    assert result.weights == {"shape": 0.50, "symmetry": 0.25, "balance": 0.25}


# Missing symmetry leaves shape and balance, rescaled by their 0.75 share.
def test_missing_symmetry_renormalises_remaining_weights():
    result = score_composite(0.80, None, 0.40)
    expected = (0.50 * 0.80 + 0.25 * 0.40) / 0.75
    assert result.compatibility_score == approx(expected)
    assert result.weights["shape"] == approx(0.50 / 0.75)
    assert result.weights["balance"] == approx(0.25 / 0.75)
    assert "symmetry" not in result.weights


# No usable term means the index is withheld, not reported as zero.
def test_no_terms_leaves_index_empty():
    result = score_composite(None, None, None)
    assert result.compatibility_score is None
    assert result.grooming_suitability_index is None
    assert result.weights == {}
