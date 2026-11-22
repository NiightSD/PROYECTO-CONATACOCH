"""
Utilidades de seguridad OWASP para CONATACOCH Fase 2.

Controles implementados:
  * Hashing de passwords con Argon2id (OWASP Password Storage Cheat Sheet).
  * Anti-fuerza bruta: bloqueo temporal de 15 min tras 5 intentos fallidos.
  * Sanitizacion de entradas para prevenir inyeccion NoSQL en MongoDB.
  * Manejo global de excepciones sin stack traces expuestos.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import math
import re
import time
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("core.security")


# -----------------------------------------------------------------------------
# 1. ARGON2ID - Hashing de passwords
# -----------------------------------------------------------------------------
def hash_password_argon2id(password: str) -> str:
    """
    Hashea un password usando Argon2id con parametros OWASP recomendados.

    Parametros (OWASP Argon2id Cheat Sheet, 2026):
      * time_cost=3, memory_cost=65536 KiB (64 MiB), parallelism=4.
    """
    from argon2 import PasswordHasher, Type

    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
        type=Type.ID,  # Argon2id
    )
    # Prefijo "argon2$" para compatibilidad con django.contrib.auth.hashers
    # (Argon2PasswordHasher). Django omite el '$' inicial de argon2-cffi.
    return "argon2$" + ph.hash(password).lstrip("$")


def _hash_sin_prefijo_django(hash_value: str) -> str:
    """Convierte el formato Django ('argon2$argon2id$...') al de argon2-cffi."""
    if hash_value.startswith("argon2$"):
        resto = hash_value[len("argon2$"):]
        return resto if resto.startswith("$") else "$" + resto
    return hash_value


def verify_password_argon2id(password: str, hash_value: str) -> bool:
    """Verifica un password contra su hash Argon2id. Retorna False si falla."""
    from argon2 import PasswordHasher, Type
    from argon2.exceptions import InvalidHashError, VerifyMismatchError

    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )
    try:
        ph.verify(_hash_sin_prefijo_django(hash_value), password)
        return True
    except VerifyMismatchError:
        return False
    except InvalidHashError:
        logger.warning("Hash almacenado no es Argon2 valido (se requiere rehash).")
        return False
    except Exception as exc:  # pragma: no cover - defensa en profundidad
        logger.warning("Error verificando hash Argon2id: %s", exc)
        return False


def needs_argon2_rehash(hash_value: str) -> bool:
    """Indica si el hash necesita regenerarse con nuevos parametros."""
    from argon2 import PasswordHasher, Type
    from argon2.exceptions import InvalidHashError

    try:
        ph = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        return ph.check_needs_rehash(_hash_sin_prefijo_django(hash_value))
    except InvalidHashError:
        # Hash no-Argon2 (p.ej. PBKDF2) => debe migrarse a Argon2id
        return True
    except Exception:
        return True


# -----------------------------------------------------------------------------
# 2. ANTI-FUERZA BRUTA
# -----------------------------------------------------------------------------
MAX_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 15


def usuario_esta_bloqueado(usuario) -> bool:
    """Retorna True si el usuario esta bloqueado temporalmente."""
    if not usuario.bloqueado_hasta:
        return False
    return usuario.bloqueado_hasta > timezone.now()


def registrar_intento_fallido(usuario) -> None:
    """
    Incrementa el contador de intentos fallidos y aplica bloqueo de 15 min
    al alcanzar 5 intentos consecutivos.
    """
    usuario.intentos_fallidos += 1
    campos = ["intentos_fallidos"]
    if usuario.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
        usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=MINUTOS_BLOQUEO)
        campos.append("bloqueado_hasta")
        logger.warning(
            "Usuario %s bloqueado por %d minutos tras %d intentos fallidos.",
            usuario.email,
            MINUTOS_BLOQUEO,
            usuario.intentos_fallidos,
        )
    usuario.save(update_fields=campos)


def registrar_exito(usuario) -> None:
    """Reinicia el contador de intentos fallidos y elimina el bloqueo."""
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])


# -----------------------------------------------------------------------------
# 3. SANITIZACION CONTRA INYECCION NOSQL (MongoDB)
# -----------------------------------------------------------------------------
_PATRON_MONGO_PELIGROSO = re.compile(r"^\$|[\$\.]")


def sanitizar_para_mongo(datos: Any, campo_origen: str = "desconocido") -> Any:
    """
    Sanitiza un valor antes de enviarlo a MongoDB para evitar inyeccion NoSQL.

    Reglas:
      * Prohibe claves que empiecen con '$' o contengan '.' (operadores Mongo).
      * Rechaza dicts con claves peligrosas.
      * Limpia strings de caracteres de control.
    """
    if isinstance(datos, dict):
        resultado = {}
        for clave, valor in datos.items():
            if not isinstance(clave, str):
                raise ValueError(f"Clave no string en {campo_origen}: {clave!r}")
            if clave.startswith("$") or "." in clave:
                logger.error(
                    "Intento de inyeccion NoSQL bloqueado en %s: clave '%s'",
                    campo_origen,
                    clave,
                )
                raise ValueError(f"Nombre de campo no permitido: {clave}")
            resultado[clave] = sanitizar_para_mongo(valor, campo_origen)
        return resultado
    if isinstance(datos, list):
        return [sanitizar_para_mongo(item, campo_origen) for item in datos]
    if isinstance(datos, str):
        # Elimina caracteres de control y nulos embebidos
        return "".join(ch for ch in datos if ord(ch) >= 32)
    return datos


def validar_documento_mongo(documento: dict, campo_origen: str = "telemetria") -> dict:
    """Valida y sanitiza un documento completo para MongoDB."""
    if not isinstance(documento, dict):
        raise ValueError("El documento debe ser un objeto JSON.")
    return sanitizar_para_mongo(documento, campo_origen)


# -----------------------------------------------------------------------------
# 4. HAVERSINE - ANTI-GPS SPOOFING
# -----------------------------------------------------------------------------
RADIO_TIERRA_KM = 6371.0
VELOCIDAD_MAXIMA_KMH = 130.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia en km entre dos puntos geograficos usando Haversine.

    OWASP: validacion de integridad de datos de entrada geografica.
    """
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return RADIO_TIERRA_KM * c


def _normalizar_utc(valor):
    """Normaliza datetimes de cualquier origen a UTC naive.

    PyMongo devuelve datetimes naive (UTC) salvo que se configure
    ``tz_aware=True``, mientras que Django/DRF entregan datetimes aware.
    Restarlos directamente lanza ``TypeError``, por lo que ambos se llevan
    al mismo espacio temporal antes de calcular la velocidad.
    """
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if not isinstance(valor, datetime):
        raise TypeError(f"timestamp no soportado: {type(valor)!r}")
    if timezone.is_aware(valor):
        return valor.astimezone(dt_timezone.utc).replace(tzinfo=None)
    return valor


def calcular_velocidad_kmh(
    lat1: float, lon1: float, t1, lat2: float, lon2: float, t2
) -> float:
    """
    Calcula velocidad promedio en km/h entre dos puntos temporales.

    Acepta datetimes aware o naive (ambos se normalizan a UTC) y descarta
    deltas no positivos para evitar divisiones por cero.
    """
    distancia = haversine_km(lat1, lon1, lat2, lon2)
    t1_utc = _normalizar_utc(t1)
    t2_utc = _normalizar_utc(t2)
    delta_segundos = (t2_utc - t1_utc).total_seconds()
    if delta_segundos <= 0:
        return 0.0
    return distancia / (delta_segundos / 3600.0)


def es_velocidad_sospechosa(velocidad_kmh: float) -> bool:
    """Retorna True si la velocidad supera el umbral de 130 km/h."""
    return velocidad_kmh > VELOCIDAD_MAXIMA_KMH


# -----------------------------------------------------------------------------
# 5. MANEJO GLOBAL DE EXCEPCIONES
# -----------------------------------------------------------------------------
def custom_exception_handler(exc, context):
    """
    Wrapper del exception handler de DRF.

    Garantiza:
      * Respuesta JSON estandarizada sin stack traces.
      * Codigo de error legible para el cliente.
      * Log interno con trace completo (solo servidor).
    """
    response = drf_exception_handler(exc, context)

    if response is None:
        # Excepcion no controlada por DRF -> 500 generico sin detalles
        logger.error("Excepcion no controlada: %s", exc, exc_info=True)
        return Response(
            {
                "error": "error_interno",
                "detail": "Ha ocurrido un error interno del servidor.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Estandarizar formato de error
    datos = {"error": "error_validacion", "detail": response.data, "status_code": response.status_code}
    response.data = datos
    return response


# -----------------------------------------------------------------------------
# 6. UTILIDAD JWT - HASH DE TOKEN DE SESION
# -----------------------------------------------------------------------------
def hash_token_sesion(token: str) -> str:
    """Almacena solo el SHA-256 del token de sesion, nunca el token en claro."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generar_codigo_otp(length: int = 6) -> str:
    """Genera un codigo OTP numerico de 6 digitos."""
    import secrets

    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def verificar_codigo_otp(codigo_usuario: str, codigo_esperado: str) -> bool:
    """Comparacion en tiempo constante para evitar timing attacks."""
    if not codigo_usuario or not codigo_esperado:
        return False
    return hmac.compare_digest(str(codigo_usuario), str(codigo_esperado))


# -----------------------------------------------------------------------------
# VALIDADORES DE DOMINIO CHILENO (RUT y Patente)
# -----------------------------------------------------------------------------


def validar_rut_chileno(value: str) -> str:
    """Valida RUT chileno (modulo 11) y retorna normalizado."""
    if not value:
        raise ValidationError("El RUT es obligatorio.")
    limpio = re.sub(r"[.\-\s]", "", str(value)).upper()
    if not re.fullmatch(r"\d{7,8}[0-9K]", limpio):
        raise ValidationError("Formato de RUT invalido. Ejemplo: 11.111.111-1")
    cuerpo, dv = limpio[:-1], limpio[-1]
    suma = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(cuerpo)))
    resto = 11 - (suma % 11)
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    if dv != esperado:
        raise ValidationError("Digito verificador de RUT invalido.")
    return limpio


def validar_patente_chilena(value: str) -> str:
    """Valida formato de patente chilena."""
    if not value:
        raise ValidationError("La patente es obligatoria.")
    limpio = value.strip().upper()
    if not re.fullmatch(r"^[A-Z]{2,4}-?[0-9]{2,4}$", limpio):
        raise ValidationError(
            "Patente invalida. Formatos: ABCD-12, AB-1234, BBBB12."
        )
    return limpio

