import unittest
from unittest.mock import patch
import sqlite3
from fastapi.testclient import TestClient
from app import app

class TestCanibalizacion(unittest.TestCase):
    def setUp(self):
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)

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

    @patch('app.enviar_correo')
    def test_guardar_registro_fecha_valida(self, mock_enviar_correo):
        payload = {
            "fecha": "2026-07-04",
            "fecha_registro": "2026-07-04",
            "maquina_donante": "Maquina A",
            "maquina_receptora": "Maquina B",
            "repuesto_nombre": "Rodamiento Test",
            "repuesto_descripcion": "Rodamiento de prueba",
            "cantidad": 1,
            "razon": "Prueba unitaria",
            "orden_trabajo": "OT-TEST",
            "retirado_por": "Tester",
            "plan_accion": "Prueba de accion",
            "tiempo_reposicion": "2026-07-10",
            "responsable_reposicion": "Responsable Test"
        }
        registro_id = None
        try:
            response = self.client.post("/guardar", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("mensaje", data)
            self.assertEqual(data["mensaje"], "Registro guardado correctamente")
            self.assertIn("id", data)
            registro_id = data["id"]
        finally:
            if registro_id:
                conn = sqlite3.connect("canibalizacion.db")
                conn.execute("DELETE FROM registros WHERE id = ?", (registro_id,))
                conn.commit()
                conn.close()

    @patch('app.enviar_correo')
    def test_guardar_registro_fecha_futura(self, mock_enviar_correo):
        payload = {
            "fecha": "2026-07-05",  # Fecha futura respecto a fecha_registro (2026-07-04)
            "fecha_registro": "2026-07-04",
            "maquina_donante": "Maquina A",
            "maquina_receptora": "Maquina B",
            "repuesto_nombre": "Rodamiento Test Futuro",
            "repuesto_descripcion": "Rodamiento de prueba futuro",
            "cantidad": 1,
            "razon": "Prueba unitaria",
            "orden_trabajo": "OT-TEST",
            "retirado_por": "Tester",
            "plan_accion": "Prueba de accion",
            "tiempo_reposicion": "2026-07-10",
            "responsable_reposicion": "Responsable Test"
        }
        response = self.client.post("/guardar", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "La fecha del evento no puede ser posterior a la fecha de hoy.")

    @patch('app.enviar_correo')
    def test_guardar_registro_reposicion_pasada(self, mock_enviar_correo):
        payload = {
            "fecha": "2026-07-04",
            "fecha_registro": "2026-07-04",
            "maquina_donante": "Maquina A",
            "maquina_receptora": "Maquina B",
            "repuesto_nombre": "Rodamiento Test Pasado",
            "repuesto_descripcion": "Rodamiento de prueba pasado",
            "cantidad": 1,
            "razon": "Prueba unitaria",
            "orden_trabajo": "OT-TEST",
            "retirado_por": "Tester",
            "plan_accion": "Prueba de accion",
            "tiempo_reposicion": "2026-07-03",  # Fecha pasada respecto a fecha_registro (2026-07-04)
            "responsable_reposicion": "Responsable Test"
        }
        response = self.client.post("/guardar", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "La fecha estimada de reposición no puede ser anterior a la fecha de hoy.")

    def test_editar_fecha_reposicion_pasada(self):
        from app import ACTIVE_SESSIONS
        import time
        token = "test-token-validation"
        ACTIVE_SESSIONS[token] = {
            "usuario": "admin",
            "rol": "admin",
            "nombre": "Administrador Test",
            "last_activity": time.time()
        }
        try:
            from datetime import date, timedelta
            ayer = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            payload = {
                "registro_id": "dummy-id",
                "nueva_fecha": ayer,
                "token": token
            }
            response = self.client.post("/api/registros/editar_fecha", json=payload)
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertEqual(data["detail"], "La nueva fecha estimada de reposición no puede ser anterior al día de hoy.")
        finally:
            if token in ACTIVE_SESSIONS:
                del ACTIVE_SESSIONS[token]

if __name__ == '__main__':
    unittest.main()
