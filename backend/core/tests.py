"""
Pruebas automatizadas de la Fase 1.

Cobertura:
  * Carga idempotente del dataset (dos ejecuciones => mismos totales).
  * Hashes de password, cifrado TOTP y token de sesion hasheado.
  * Validacion de RUT y proteccion ON DELETE RESTRICT (PROTECT).
  * API publica, JWT y no exposicion de secretos.
"""
from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models import ProtectedError
from django.test import TestCase, override_settings

from core.models import (
    Conductor,
    LineaColectiva,
    Paradero,
    Usuario,
    Vehiculo,
)
from core.models import validar_rut


class SeedIdempotenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        salida = StringIO()
        call_command("seed_conatacoch", "--skip-paraderos", stdout=salida)
        cls.primera_salida = salida.getvalue()

    def test_dataset_completo(self):
        self.assertEqual(LineaColectiva.objects.count(), 660)
        self.assertEqual(LineaColectiva.objects.values("folio").distinct().count(), 396)
        self.assertEqual(Paradero.objects.count(), 0)  # omitidos en el setUp

    def test_usuarios_y_flota_demo(self):
        self.assertEqual(Usuario.objects.count(), 5)
        self.assertEqual(Vehiculo.objects.count(), 2)
        self.assertEqual(Conductor.objects.count(), 2)

        admin = Usuario.objects.get(rut="11.111.111-1")
        self.assertTrue(admin.check_password("AdminConata2026!"))
        self.assertEqual(admin.rol, Usuario.Rol.ADMIN)
        self.assertTrue(admin.is_staff and admin.is_superuser)
        self.assertTrue(admin.is_active)

        conductor = Conductor.objects.get(folio_conatacoch="234001")
        self.assertEqual(conductor.vehiculo.patente, "ABCD-12")
        self.assertTrue(conductor.get_otp_secreto())
        self.assertEqual(conductor.token_sesion_activa, "")

    def test_segunda_ejecucion_no_duplica(self):
        salida = StringIO()
        call_command("seed_conatacoch", "--skip-paraderos", stdout=salida)
        self.assertEqual(LineaColectiva.objects.count(), 660)
        self.assertEqual(Usuario.objects.count(), 5)
        self.assertEqual(Vehiculo.objects.count(), 2)
        self.assertEqual(Conductor.objects.count(), 2)
        self.assertIn("Lineas creadas      : 0", salida.getvalue())
        self.assertIn("Lineas actualizadas : 660", salida.getvalue())

    def test_rut_invalido(self):
        with self.assertRaises(ValidationError):
            validar_rut("11.111.111-9")

    def test_protect_impide_borrar_linea_referenciada(self):
        vehiculo = Vehiculo.objects.get(patente="ABCD-12")
        with self.assertRaises(ProtectedError):
            vehiculo.linea.delete()


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "seed_conatacoch",
            "--skip-paraderos",
            stdout=StringIO(),
        )

    def test_health_live_publico(self):
        respuesta = self.client.get("/api/health/live/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["status"], "ok")

    @patch("core.views.mongo.ping", return_value=(False, 1.5))
    def test_health_degradado_sin_mongo(self, _ping):
        respuesta = self.client.get("/api/health/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["status"], "degraded")
        self.assertEqual(respuesta.json()["components"]["mongodb"]["status"], "error")

    def test_stats_publicas(self):
        respuesta = self.client.get("/api/stats/")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["lineas"], 660)
        self.assertEqual(datos["folios"], 396)
        self.assertEqual(datos["comunas"], 48)
        self.assertEqual(datos["conductores"], 2)

    def test_lineas_publicas_y_filtro(self):
        respuesta = self.client.get("/api/lineas/?comuna=Melipilla&page_size=5")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertGreater(datos["count"], 0)
        self.assertLessEqual(len(datos["results"]), 5)

    def test_flota_requiere_jwt(self):
        self.assertEqual(self.client.get("/api/conductores/").status_code, 401)

        token = self.client.post(
            "/api/token/",
            data=json.dumps(
                {"email": "admin@conatacoch.cl", "password": "AdminConata2026!"}
            ),
            content_type="application/json",
        )
        self.assertEqual(token.status_code, 200)
        access = token.json()["access"]

        respuesta = self.client.get(
            "/api/conductores/", HTTP_AUTHORIZATION=f"Bearer {access}"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["count"], 2)
        registro = respuesta.json()["results"][0]
        self.assertNotIn("otp_secreto", registro)
        self.assertNotIn("token_sesion_activa", registro)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            },
        }
    )
    def test_esquema_openapi_y_docs(self):
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)
