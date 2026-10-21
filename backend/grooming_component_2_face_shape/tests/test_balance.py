from face_shape.contracts import ClassificationInput, LandmarkPoint, Tier1Landmarks, Tier2Landmarks
from face_shape.geometry import prepare_landmarks
from face_shape.score.balance import score_balance


def _pt(x: float, y: float) -> LandmarkPoint:
    return LandmarkPoint.model_validate({"x": x, "y": y, "visible": True})


def _vertical_sample(lower_end: float = 300.0, include_hairline: bool = True) -> ClassificationInput:
    extra = {
        "glabella": _pt(0.0, 100.0),
        "subnasale": _pt(0.0, 200.0),
        "endocanthion_r": _pt(-10.0, 140.0),
        "endocanthion_l": _pt(10.0, 140.0),
        "exocanthion_r": _pt(-30.0, 140.0),
        "exocanthion_l": _pt(30.0, 140.0),
    }
    trichion = _pt(0.0, 0.0) if include_hairline else None
    return ClassificationInput(
        tier1=Tier1Landmarks(
            nasion=_pt(0.0, 80.0),
            menton=_pt(0.0, lower_end),
            zygion_l=_pt(50.0, 140.0),
            zygion_r=_pt(-50.0, 140.0),
            gonion_l=_pt(40.0, 250.0),
            gonion_r=_pt(-40.0, 250.0),
            frontotemporale_l=_pt(40.0, 40.0),
            frontotemporale_r=_pt(-40.0, 40.0),
        ),
        tier2=Tier2Landmarks(trichion=trichion),
        extra=extra,
    )


def test_equal_thirds_score_high():
    result = score_balance(prepare_landmarks(_vertical_sample()))
    assert result.vertical_balance_score is not None
    assert result.vertical_balance_score > 0.9
    assert result.thirds["p1"] == result.thirds["p2"] == result.thirds["p3"]


def test_stretched_lower_third_lowers_vertical_score():
    even = score_balance(prepare_landmarks(_vertical_sample(300.0)))
    long_lower = score_balance(prepare_landmarks(_vertical_sample(420.0)))
    assert even.vertical_balance_score is not None
    assert long_lower.vertical_balance_score is not None
    assert long_lower.vertical_balance_score < even.vertical_balance_score


def test_missing_trichion_flags_limited_upper_third():
    result = score_balance(prepare_landmarks(_vertical_sample(include_hairline=False)))
    assert "limited_upper_third" in result.notes
    assert "p1" not in result.thirds
    assert result.vertical_balance_score is not None


def test_equal_fifths_score_high():
    result = score_balance(prepare_landmarks(_vertical_sample()))
    assert result.horizontal_balance_score is not None
    assert result.horizontal_balance_score > 0.95
    assert result.balance_score is not None
