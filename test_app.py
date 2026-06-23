import unittest
from fastapi.testclient import TestClient
from app import app

class TestCanibalizacion(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_obtener_equipos(self):
        response = self.client.get("/api/equipos")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        if "error" not in data:
            self.assertIn("divisiones", data)

    def test_obtener_registros(self):
        response = self.client.get("/api/registros")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("canibalizaciones", data)

if __name__ == '__main__':
    unittest.main()
