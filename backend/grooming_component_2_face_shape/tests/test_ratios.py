import pytest

from face_shape.contracts import ClassificationInput, LandmarkPoint, RatioFeatures, Tier1Landmarks
from face_shape.geometry import prepare_landmarks
from face_shape.indices import DegenerateMeasurement, measure_ratios
from face_shape.membership import confidence_vector, geometric_mean, tier1_scores, trapezoid_membership
from face_shape.thresholds import CLASS_TRAPEZOIDS


def _point(x: float, y: float, z: float | None = None) -> LandmarkPoint:
    payload = {"x": x, "y": y}
    if z is not None:
        payload["z"] = z
    return LandmarkPoint.model_validate(payload)


def _sample(scale: float = 1.0, z: float | None = None, skew_depth: bool = False) -> ClassificationInput:
    def located(x: float, y: float, depth: float | None = z) -> LandmarkPoint:
        return _point(x * scale, y * scale, depth)

    right_depth = -20.0 if skew_depth else z
    left_depth = 30.0 if skew_depth else z
    return ClassificationInput(
        tier1=Tier1Landmarks(
            nasion=located(0.0, 0.0),
            menton=located(0.0, 87.0),
            zygion_left=located(-50.0, 40.0, left_depth),
            zygion_right=located(50.0, 40.0, right_depth),
            gonion_left=located(-39.0, 70.0),
            gonion_right=located(39.0, 70.0),
            frontotemporale_left=located(-39.0, 15.0),
            frontotemporale_right=located(39.0, 15.0),
        )
    )


def test_trichion_sets_total_face_ratio():
    sample = _sample()
    sample.tier2.trichion = _point(0.0, -40.0)
    prepared = prepare_landmarks(sample)

    assert measure_ratios(prepared).tfi == pytest.approx(1.27)


def test_pixel_coordinates_produce_percentage_indices():
    prepared = prepare_landmarks(_sample(scale=4.0))
    ratios = measure_ratios(prepared)

    assert prepared.frame == "image_2d"
    assert prepared.scale == "pixel"
    assert ratios.mfi == pytest.approx(87.0)
    assert ratios.jmi == pytest.approx(78.0)
    assert ratios.fzi == pytest.approx(78.0)
    assert ratios.tfi is None


def test_normalized_and_pixel_inputs_share_ratios():
    pixel = measure_ratios(prepare_landmarks(_sample(scale=4.0)))
    normalized = measure_ratios(prepare_landmarks(_sample(scale=0.01)))

    assert prepare_landmarks(_sample(scale=0.01)).scale == "normalized"
    assert normalized.mfi == pytest.approx(pixel.mfi)
    assert normalized.jmi == pytest.approx(pixel.jmi)
    assert normalized.fzi == pytest.approx(pixel.fzi)


def test_depth_is_projected_away_before_ratios():
    flat = measure_ratios(prepare_landmarks(_sample()))
    skewed = prepare_landmarks(_sample(z=5.0, skew_depth=True))
    projected = measure_ratios(skewed)

    assert skewed.frame == "projected_3d"
    assert projected.mfi == pytest.approx(flat.mfi)
    assert projected.jmi == pytest.approx(flat.jmi)
    assert projected.fzi == pytest.approx(flat.fzi)


def test_partial_depth_still_uses_the_frontal_plane():
    sample = _sample()
    sample.tier1.nasion = _point(0.0, 0.0, 0.2)
    prepared = prepare_landmarks(sample)

    assert prepared.frame == "partial_depth"
    assert measure_ratios(prepared).mfi == pytest.approx(87.0)


def test_zero_bizygomatic_breadth_is_rejected():
    sample = _sample()
    sample.tier1.zygion_right = _point(-50.0, 40.0)

    with pytest.raises(DegenerateMeasurement):
        measure_ratios(prepare_landmarks(sample))


def test_trapezoid_plateau_and_ramps():
    oval_jmi = CLASS_TRAPEZOIDS["oval"]["jmi"]

    assert trapezoid_membership(78.0, oval_jmi) == 1.0
    assert trapezoid_membership(83.0, oval_jmi) == pytest.approx(0.5)
    assert trapezoid_membership(83.0, CLASS_TRAPEZOIDS["square"]["jmi"]) == pytest.approx(0.5)
    assert trapezoid_membership(70.0, oval_jmi) == 0.0


def test_oval_prototype_scores_itself_at_one():
    ratios = RatioFeatures(mfi=87.0, jmi=78.0, fzi=78.0)
    scores = tier1_scores(ratios)
    confidence = confidence_vector(scores)

    assert scores["oval"] == 1.0
    assert confidence["oval"] == max(confidence.values())
    assert sum(confidence.values()) == pytest.approx(1.0)


def test_geometric_mean_blocks_a_zero_feature():
    assert geometric_mean([1.0, 0.0, 1.0]) == 0.0
    assert geometric_mean([0.25, 0.25, 0.25]) == pytest.approx(0.25)
