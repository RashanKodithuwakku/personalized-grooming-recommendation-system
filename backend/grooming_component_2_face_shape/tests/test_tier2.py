"""Tier 2 checks: TFI and jaw type on top of the tier-1 scores.

TFI above 1.55 can select oblong. Jaw type matters only near JMI 83.
"""

import pytest

from face_shape.tier1 import classify_tier1
from face_shape.tier2 import classify_face
from tests.helpers import face


# No trichion and no jaw label: tier 2 must match tier 1 exactly.
def test_without_modifiers_the_label_matches_tier1():
    sample = face(87.0, 78.0, 78.0)
    assert classify_face(sample).face_type == classify_tier1(sample).face_type
    assert classify_face(sample).modifiers_applied == []


# TFI 1.60 is inside the oblong core, so the modifier is recorded.
def test_high_total_face_ratio_selects_oblong():
    sample = face(87.0, 78.0, 84.0, tfi=1.60)
    result = classify_face(sample)
    assert result.face_type == "oblong"
    assert result.modifiers_applied == ["tfi"]
    assert result.ratios.tfi == pytest.approx(1.60)


# TFI 1.30 is a typical face and must not trigger the oblong rule.
def test_typical_total_face_ratio_does_not_apply():
    sample = face(87.0, 78.0, 84.0, tfi=1.30)
    result = classify_face(sample)
    assert result.modifiers_applied == []
    assert result.face_type == classify_tier1(sample).face_type


# A long total face reduces oval confidence even if MFI still looks oval.
def test_tfi_penalises_oval_when_the_face_is_long():
    plain = classify_face(face(87.0, 78.0, 78.0))
    long_face = classify_face(face(87.0, 78.0, 78.0, tfi=1.60))
    assert long_face.face_type_confidence["oval"] < plain.face_type_confidence["oval"]


# At JMI 83 an angular jaw moves the tie from oval to square.
def test_angular_jaw_in_the_tie_band_selects_square():
    sample = face(87.0, 83.0, 83.0, jaw="angular")
    result = classify_face(sample)
    assert classify_tier1(sample).face_type == "oval"
    assert result.face_type == "square"
    assert result.modifiers_applied == ["jaw_type"]


# At JMI 83 a rounded jaw supports round.
def test_rounded_jaw_in_the_tie_band_selects_round():
    sample = face(80.0, 83.0, 86.0, jaw="rounded")
    result = classify_face(sample)
    assert result.face_type == "round"
    assert result.modifiers_applied == ["jaw_type"]


# JMI 90 is already square, so the jaw rule adds nothing.
def test_jaw_outside_the_tie_band_is_not_applied():
    sample = face(87.0, 90.0, 86.0, jaw="angular")
    result = classify_face(sample)
    assert result.face_type == "square"
    assert result.modifiers_applied == []


# Tapered is recorded by Component 1 but does not boost or suppress a class.
def test_tapered_jaw_does_not_move_the_scores():
    plain = face(87.0, 83.0, 83.0)
    tapered = face(87.0, 83.0, 83.0, jaw="tapered")
    assert classify_face(tapered).face_type == classify_face(plain).face_type
    assert classify_face(tapered).modifiers_applied == []


# TFI is listed before jaw type. Zero jaw confidence applies TFI only.
def test_both_modifiers_are_recorded_in_order():
    sample = face(87.0, 83.0, 84.0, tfi=1.60, jaw="angular", jaw_confidence=0.0)
    assert classify_face(sample).modifiers_applied == ["tfi"]
    moved = face(87.0, 83.0, 84.0, tfi=1.60, jaw="angular")
    assert classify_face(moved).modifiers_applied == ["tfi", "jaw_type"]
