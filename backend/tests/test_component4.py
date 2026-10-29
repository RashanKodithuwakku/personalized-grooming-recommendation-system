import os
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.blending import blend_template
from app.comparison import calculate_preview_metrics, create_before_after
from app.explanation import generate_explanation
from app.hairfastgan import get_status
from app.database import init_db, save_feedback, get_all_feedback
from app.landmarks import get_user_landmarks


class Component4UnitTests(unittest.TestCase):
    def test_blending_preserves_background_when_mask_empty(self):
        base = np.full((32, 32, 3), 120, dtype=np.uint8)
        layer = np.full((32, 32, 3), 220, dtype=np.uint8)
        result = blend_template(layer, base, np.zeros((32, 32), dtype=np.uint8))
        self.assertTrue(np.array_equal(result, base))

    def test_before_after_and_metrics(self):
        before = np.zeros((30, 40, 3), dtype=np.uint8)
        after = before.copy()
        after[5:10, 5:10] = 255
        combined = create_before_after(before, after)
        metrics = calculate_preview_metrics(before, after)
        self.assertEqual(combined.shape[0], 30)
        self.assertGreater(metrics['changed_pixel_percent'], 0)
        self.assertGreater(metrics['mean_absolute_pixel_difference'], 0)

    def test_explanation_is_grounded_in_provided_scores(self):
        text = generate_explanation({
            'match_score': 0.8,
            'confidence': 0.7,
            'contributing_factors': {'face_width': 0.9, 'hair_coverage': 0.6},
        })
        self.assertIn('face-width', text)
        self.assertIn('80%', text)
        self.assertIn('70%', text)

    def test_feedback_round_trip(self):
        # Use a temporary DB by monkey-patching the module constant.
        import app.database as db
        old_path = db.DB_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            db.DB_PATH = os.path.join(temp_dir, 'feedback.sqlite')
            try:
                db.init_db()
                saved = db.save_feedback('test', 'crew_cut', 'crew_cut_A', 'like', 'hairstyle', 1)
                rows = db.get_all_feedback()
                self.assertEqual(saved['feedback'], 'like')
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['style_type'], 'hairstyle')
            finally:
                db.DB_PATH = old_path

    def test_hairfastgan_unconfigured_is_explicit(self):
        old = os.environ.pop('HAIRFASTGAN_COMMAND', None)
        try:
            self.assertFalse(get_status()['configured'])
        finally:
            if old is not None:
                os.environ['HAIRFASTGAN_COMMAND'] = old

    def test_landmarks_invalid_image_fails_clearly(self):
        with self.assertRaises(FileNotFoundError):
            get_user_landmarks('/definitely/not/a/real/photo.jpg')


if __name__ == '__main__':
    unittest.main()
