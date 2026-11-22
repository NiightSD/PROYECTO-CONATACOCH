"""
Cifrado simetrico para secretos reversibles (TOTP de conductores).

Los secretos TOTP deben poder recuperarse para validar codigos, por lo que no
se pueden hashear. Se cifran con Fernet (AES-128-CBC + HMAC-SHA256) derivando
la clave desde SECRET_KEY / OTP_ENCRYPTION_KEY.

Nota de produccion: para rotacion de claves se recomienda un KMS (AWS KMS,
GCP KMS o Azure Key Vault) en lugar de derivar desde SECRET_KEY.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _build_fernet() -> Fernet:
    base = getattr(settings, "OTP_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    if not base:
        raise ImproperlyConfigured("SECRET_KEY es obligatoria para cifrar OTP.")
    digest = hashlib.sha256(base.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def cifrar_secreto(valor: str) -> str:
    """Cifra un secreto en texto plano y retorna un token URL-safe."""
    if not valor:
        return ""
    return _build_fernet().encrypt(valor.encode("utf-8")).decode("ascii")


def descifrar_secreto(token: str) -> str:
    """Descifra un token Fernet. Retorna '' si el token es invalido/vacio."""
    if not token:
        return ""
    try:
        return _build_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""
