import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient
from app.main import app


class Component4ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint_reports_optional_model_state(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertIn('model_loaded', response.json())
        self.assertIn('hairfastgan', response.json())

    def test_styles_endpoint_returns_available_ranked_styles(self):
        response = self.client.get('/styles?gender=male&style_type=hairstyle')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertLessEqual(len(body['styles']), 5)
        self.assertEqual([item['rank'] for item in body['styles']], sorted(item['rank'] for item in body['styles']))

    def test_invalid_gender_is_rejected(self):
        response = self.client.get('/styles?gender=other&style_type=hairstyle')
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
