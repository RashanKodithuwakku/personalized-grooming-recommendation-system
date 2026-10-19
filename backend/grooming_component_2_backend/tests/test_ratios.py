import pytest

from face_shape.contracts import ImageSpec, RatioFeatures
from face_shape.geometry import prepare_landmarks
from face_shape.indices import DegenerateMeasurement, measure_ratios
from face_shape.membership import confidence_vector, geometric_mean, tier1_scores, trapezoid_membership
from face_shape.rules import morphological_class
from face_shape.thresholds import CLASS_TRAPEZOIDS
from tests.helpers import face, point


def test_trichion_sets_total_face_ratio():
    sample = face(87.0, 78.0, 78.0, tfi=1.27)
    prepared = prepare_landmarks(sample)
    assert measure_ratios(prepared).tfi == pytest.approx(1.27)


def test_pixel_coordinates_produce_percentage_indices():
    prepared = prepare_landmarks(face(87.0, 78.0, 78.0, scale=4.0))
    ratios = measure_ratios(prepared)

    assert prepared.scale == "pixel"
    assert ratios.mfi == pytest.approx(87.0)
    assert ratios.jmi == pytest.approx(78.0)
    assert ratios.fzi == pytest.approx(78.0)
    assert ratios.tfi is None


def test_normalized_non_square_image_is_converted_to_pixels():
    image = ImageSpec(width=1080, height=1440, coordinate_mode="normalized")
    sample = face(87.0, 78.0, 78.0, image=image, scale=0.001)
    ratios = measure_ratios(prepare_landmarks(sample))
    pixel = measure_ratios(prepare_landmarks(face(87.0, 78.0, 78.0)))
    assert ratios.jmi == pytest.approx(pixel.jmi)
    assert ratios.mfi != pytest.approx(pixel.mfi)


def test_depth_is_projected_away_before_ratios():
    flat = measure_ratios(prepare_landmarks(face(87.0, 78.0, 78.0)))
    skewed = face(87.0, 78.0, 78.0, z=5.0)
    skewed.tier1.zygion_l = point(-50.0, 40.0, 30.0)
    skewed.tier1.zygion_r = point(50.0, 40.0, -20.0)
    projected = measure_ratios(prepare_landmarks(skewed))
    assert projected.mfi == pytest.approx(flat.mfi)
    assert projected.jmi == pytest.approx(flat.jmi)


def test_missing_frontotemporale_omits_fzi():
    ratios = measure_ratios(prepare_landmarks(face(87.0, 78.0, fzi=None)))
    assert ratios.fzi is None
    assert ratios.mfi == pytest.approx(87.0)


def test_zero_bizygomatic_breadth_is_rejected():
    sample = face(87.0, 78.0, 78.0)
    sample.tier1.zygion_r = point(-50.0, 40.0)
    with pytest.raises(DegenerateMeasurement):
        measure_ratios(prepare_landmarks(sample))


def test_trapezoid_plateau_and_ramps():
    oval_jmi = CLASS_TRAPEZOIDS["oval"]["jmi"]
    assert trapezoid_membership(78.0, oval_jmi) == 1.0
    assert trapezoid_membership(83.0, oval_jmi) == 1.0
    assert trapezoid_membership(83.0, CLASS_TRAPEZOIDS["square"]["jmi"]) == 1.0
    assert trapezoid_membership(70.0, oval_jmi) == 0.0


def test_oval_prototype_scores_itself_at_one():
    ratios = RatioFeatures(mfi=87.0, jmi=78.0, fzi=78.0)
    scores = tier1_scores(ratios)
    confidence = confidence_vector(scores)
    assert scores["oval"] == pytest.approx(1.0)
    assert confidence["oval"] == max(confidence.values())
    assert morphological_class(87.0) == "Mesoprosopic"


def test_geometric_mean_blocks_a_zero_feature():
    assert geometric_mean([1.0, 0.0, 1.0]) == 0.0
    assert geometric_mean([0.25, 0.25, 0.25]) == pytest.approx(0.25)
