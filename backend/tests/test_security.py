"""
Pruebas unitarias de seguridad (Fase 2):
  * Argon2id hashing y verificacion de passwords.
  * Calculo de ETA.
  * Filtro cinematico Haversine anti-GPS-spoofing.
"""
from __future__ import annotations

import hashlib
import math
import time

import pytest
from argon2 import PasswordHasher
from django.utils import timezone

from core.security import (
    hash_password_argon2id,
    verify_password_argon2id,
    needs_argon2_rehash,
    haversine_km,
    calcular_velocidad_kmh,
    es_velocidad_sospechosa,
    VELOCIDAD_MAXIMA_KMH,
    validar_documento_mongo,
    sanitizar_para_mongo,
)


# ---------------------------------------------------------------------------
# Argon2id
# ---------------------------------------------------------------------------
class TestArgon2id:
    def test_hash_y_verifica_password_correcto(self):
        password = "Conduc2026!Seguro"
        hash_valor = hash_password_argon2id(password)
        assert hash_valor != password
        assert verify_password_argon2id(password, hash_valor) is True

    def test_rechaza_password_incorrecto(self):
        hash_valor = hash_password_argon2id("password_correcto")
        assert verify_password_argon2id("password_incorrecto", hash_valor) is False

    def test_hash_es_deterministico_con_salt_distinto(self):
        # Argon2 usa salt aleatorio, dos hashes del mismo password difieren
        h1 = hash_password_argon2id("mismapassword")
        h2 = hash_password_argon2id("mismapassword")
        assert h1 != h2

    def test_needs_rehash_detecta_parametros_antiguos(self):
        # Hashear con PBKDF2 (antiguo) y detectar que necesita rehash a Argon2id
        from django.contrib.auth.hashers import make_password
        hash_pbkdf2 = make_password("contraseña")
        assert needs_argon2_rehash(hash_pbkdf2) is True

    def test_identifica_hash_argon2_valido(self):
        ph = PasswordHasher()
        hash_argon2 = ph.hash("test123")
        assert needs_argon2_rehash(hash_argon2) is False


# ---------------------------------------------------------------------------
# ETA
# ---------------------------------------------------------------------------
class TestCalculoETA:
    def test_eta_conductor_cercano(self):
        """ETA para pasajero cerca del conductor debe ser bajo."""
        from core.security import haversine_km

        # Mismo punto: distancia 0
        dist = haversine_km(-33.4489, -70.6693, -33.4489, -70.6693)
        assert dist == 0.0

        # Aproximadamente 1 km de distancia
        dist = haversine_km(-33.4489, -70.6693, -33.4489, -70.6783)
        assert 0.8 < dist < 1.5

    def test_velocidad_calculada_delta_tiempo(self):
        """Velocidad entre dos puntos con delta de tiempo conocido."""
        from datetime import datetime, timedelta, timezone as tz

        t1 = datetime(2026, 11, 21, 14, 0, 0, tzinfo=tz.utc)
        t2 = datetime(2026, 11, 21, 14, 6, 0, tzinfo=tz.utc)  # 6 min despues

        # ~0.84 km en 6 min (0.1 h) = ~8.4 km/h
        velocidad = calcular_velocidad_kmh(
            -33.4489, -70.6693, t1, -33.4489, -70.6783, t2
        )
        assert 7 < velocidad < 10

    def test_velocidad_delta_cero_no_divide_por_cero(self):
        """Delta no positivo retorna 0 en vez de lanzar o inflar la velocidad."""
        from datetime import datetime, timezone as tz

        t1 = datetime(2026, 11, 21, 14, 0, 0, tzinfo=tz.utc)
        t2 = datetime(2026, 11, 21, 14, 0, 0, tzinfo=tz.utc)

        velocidad = calcular_velocidad_kmh(-33.4489, -70.6693, t1, -33.4489, -70.6783, t2)
        assert velocidad == 0.0

    def test_velocidad_mezcla_datetime_naive_y_aware(self):
        """PyMongo entrega naive y Django aware: deben poder restarse."""
        from datetime import datetime, timezone as tz

        t1_naive = datetime(2026, 11, 21, 14, 0, 0)  # como lo devuelve PyMongo
        t2_aware = datetime(2026, 11, 21, 14, 6, 0, tzinfo=tz.utc)

        velocidad = calcular_velocidad_kmh(
            -33.4489, -70.6693, t1_naive, -33.4489, -70.6783, t2_aware
        )
        assert 7 < velocidad < 10


# ---------------------------------------------------------------------------
# Haversine Anti-Spoofing
# ---------------------------------------------------------------------------
class TestAntiSpoofingHaversine:
    def test_velocidad_normal_no_es_sospechosa(self):
        assert es_velocidad_sospechosa(50.0) is False
        assert es_velocidad_sospechosa(100.0) is False
        assert es_velocidad_sospechosa(130.0) is False  # umbral exacto

    def test_velocidad_supera_umbral_es_sospechosa(self):
        assert es_velocidad_sospechosa(130.1) is True
        assert es_velocidad_sospechosa(200.0) is True

    def test_distancia_santiago_providencia(self):
        """Distancia aproximada entre Santiago y Providencia."""
        dist = haversine_km(-33.4489, -70.6693, -33.4370, -70.6500)
        assert 1.5 < dist < 2.5  # ~2 km

    def test_distancia_misma_coordenada_es_cero(self):
        d = haversine_km(-33.4489, -70.6693, -33.4489, -70.6693)
        assert d == 0.0


# ---------------------------------------------------------------------------
# Sanitizacion NoSQL
# ---------------------------------------------------------------------------
class TestSanitizacionNoSQL:
    def test_rechaza_clave_con_dolar(self):
        with pytest.raises(ValueError):
            sanitizar_para_mongo({"$where": "1==1"})

    def test_rechaza_clave_con_punto(self):
        with pytest.raises(ValueError):
            sanitizar_para_mongo({"a.b": "valor"})

    def test_rechaza_documento_anidado_con_operador(self):
        with pytest.raises(ValueError):
            sanitizar_para_mongo({"usuario": {"$gt": ""}})

    def test_documento_valido_pasa_sin_cambios(self):
        doc = validar_documento_mongo(
            {"nombre": "test", "valor": 123, "activo": True}
        )
        assert doc == {"nombre": "test", "valor": 123, "activo": True}

    def test_limpia_caracteres_control_en_strings(self):
        resultado = sanitizar_para_mongo({"nombre": "test\x00\x01valor"})
        assert resultado == {"nombre": "testvalor"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
class TestUtilidadesSeguridad:
    def test_hash_token_sesion_no_revela_token(self):
        from core.security import hash_token_sesion

        token = "mi_token_secreto_123"
        hash_valor = hash_token_sesion(token)
        assert hash_valor != token
        assert len(hash_valor) == 64  # SHA-256 hex

    def test_generar_codigo_otp_es_numerico(self):
        from core.security import generar_codigo_otp

        codigo = generar_codigo_otp(6)
        assert len(codigo) == 6
        assert codigo.isdigit()

    def test_verificar_codigo_otp_tiempo_constante(self):
        from core.security import verificar_codigo_otp

        assert verificar_codigo_otp("123456", "123456") is True
        assert verificar_codigo_otp("123456", "654321") is False
        assert verificar_codigo_otp("", "123456") is False
        assert verificar_codigo_otp("123456", "") is False
