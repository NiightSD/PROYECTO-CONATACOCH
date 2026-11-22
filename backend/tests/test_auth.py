"""
Pruebas de autenticacion y anti-fuerza bruta (Fase 2):
  * Login con Argon2id.
  * Bloqueo tras 5 intentos fallidos (15 minutos).
  * Sesion unica con OTP para inicio de turno.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from core.models import Usuario, Conductor
from core.security import (
    registrar_intento_fallido,
    registrar_exito,
    usuario_esta_bloqueado,
    hash_password_argon2id,
    verify_password_argon2id,
)


# ---------------------------------------------------------------------------
# Login y anti-fuerza bruta
# ---------------------------------------------------------------------------
class TestLoginArgon2id:
    def test_login_exitoso_verify_argon2(self, cliente_user):
        """El password almacenado con Argon2id se verifica correctamente."""
        assert verify_password_argon2id("PasajeroPass123!", cliente_user.password) is True

    def test_login_fallo_password_incorrecto(self, cliente_user):
        assert verify_password_argon2id("password_incorrecto", cliente_user.password) is False

    def test_password_hash_no_es_texto_plano(self, cliente_user):
        assert cliente_user.password != "PasajeroPass123!"
        assert cliente_user.password.startswith("argon2")


class TestFuerzaBruta:
    def test_bloqueo_despues_de_5_intentos(self, cliente_user):
        """Tras 5 intentos fallidos, el usuario debe estar bloqueado."""
        assert usuario_esta_bloqueado(cliente_user) is False
        assert cliente_user.intentos_fallidos == 0

        for i in range(5):
            registrar_intento_fallido(cliente_user)
            cliente_user.refresh_from_db()

        assert cliente_user.intentos_fallidos == 5
        assert usuario_esta_bloqueado(cliente_user) is True
        assert cliente_user.bloqueado_hasta is not None
        assert cliente_user.bloqueado_hasta > timezone.now()

    def test_bloqueo_dura_15_minutos(self, cliente_user):
        """El bloqueo debe ser de exactamente 15 minutos."""
        for _ in range(5):
            registrar_intento_fallido(cliente_user)

        diferencia = cliente_user.bloqueado_hasta - timezone.now()
        minutos = diferencia.total_seconds() / 60
        assert 14.5 < minutos <= 15.5

    def test_login_exitoso_reinicia_contador(self, cliente_user):
        """Un login exitoso reinicia intentos fallidos y elimina bloqueo."""
        for _ in range(3):
            registrar_intento_fallido(cliente_user)

        assert cliente_user.intentos_fallidos == 3

        registrar_exito(cliente_user)
        cliente_user.refresh_from_db()
        assert cliente_user.intentos_fallidos == 0
        assert cliente_user.bloqueado_hasta is None
        assert usuario_esta_bloqueado(cliente_user) is False

    def test_usuario_no_bloqueado_con_menos_de_5(self, cliente_user):
        for _ in range(4):
            registrar_intento_fallido(cliente_user)

        assert usuario_esta_bloqueado(cliente_user) is False
        assert cliente_user.intentos_fallidos == 4


# ---------------------------------------------------------------------------
# Sesion unica con OTP (inicio de turno)
# ---------------------------------------------------------------------------
class TestSesionUnicaOTP:
    def test_conductor_no_tiene_turno_inicialmente(self, conductor):
        assert conductor.en_turno is False
        assert conductor.token_sesion_activa == ""

    def test_otp_codigo_se_genera_y_expira(self, conductor):
        from core.security import generar_codigo_otp

        codigo = generar_codigo_otp()
        conductor.otp_codigo = codigo
        conductor.otp_codigo_expira = timezone.now() + timedelta(minutes=5)
        conductor.save(update_fields=["otp_codigo", "otp_codigo_expira"])

        assert conductor.otp_codigo == codigo
        assert conductor.otp_codigo_expira > timezone.now()

    def test_otp_expira_despues_de_5_minutos(self, conductor):
        conductor.otp_codigo = "123456"
        conductor.otp_codigo_expira = timezone.now() - timedelta(minutes=1)
        conductor.save(update_fields=["otp_codigo", "otp_codigo_expira"])

        assert conductor.otp_codigo_expira <= timezone.now()

    def test_clear_token_sesion(self, conductor):
        conductor.token_sesion_activa = "hash_previo"
        conductor.save(update_fields=["token_sesion_activa"])
        assert conductor.token_sesion_activa == "hash_previo"

        conductor.clear_token_sesion()
        conductor.save(update_fields=["token_sesion_activa"])
        assert conductor.token_sesion_activa == ""
