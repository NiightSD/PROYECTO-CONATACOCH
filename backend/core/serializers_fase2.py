"""
Serializers de escritura y lectura para Fase 2.

Incluyen validaciones de negocio, tipado estricto y exclusion de campos sensibles.
"""
from __future__ import annotations

import re
import uuid

from django.core.exceptions import ValidationError
from rest_framework import serializers

from core.models import Conductor, LineaColectiva, TransaccionPago, Usuario, Vehiculo
from core.security import validar_rut_chileno, validar_patente_chilena


def validar_rut_chileno(value: str) -> str:
    """Valida RUT chileno (modulo 11) y retorna normalizado."""
    if not value:
        raise serializers.ValidationError("El RUT es obligatorio.")
    limpio = re.sub(r"[.\-\s]", "", str(value)).upper()
    if not re.fullmatch(r"\d{7,8}[0-9K]", limpio):
        raise serializers.ValidationError("Formato de RUT invalido. Ejemplo: 11.111.111-1")
    cuerpo, dv = limpio[:-1], limpio[-1]
    suma = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(cuerpo)))
    resto = 11 - (suma % 11)
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    if dv != esperado:
        raise serializers.ValidationError("Digito verificador de RUT invalido.")
    return limpio


def validar_patente_chilena(value: str) -> str:
    """Valida formato de patente chilena."""
    if not value:
        raise serializers.ValidationError("La patente es obligatoria.")
    limpio = value.strip().upper()
    if not re.fullmatch(r"^[A-Z]{2,4}-?[0-9]{2,4}$", limpio):
        raise serializers.ValidationError(
            "Patente invalida. Formatos: ABCD-12, AB-1234, BBBB12."
        )
    return limpio


# -----------------------------------------------------------------------------
# Autenticacion
# -----------------------------------------------------------------------------
class LoginSerializer(serializers.Serializer):
    # CharField (no EmailField) para responder siempre 401 ante entradas
    # malformadas/payloads de inyeccion, sin revelar si el email existe.
    email = serializers.CharField(required=True, max_length=254)
    password = serializers.CharField(required=True, write_only=True)


# -----------------------------------------------------------------------------
# Usuario / Conductor (solo ADMIN registra)
# -----------------------------------------------------------------------------
class UsuarioRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    rol = serializers.ChoiceField(choices=Usuario.Rol.choices, default=Usuario.Rol.CLIENTE)

    class Meta:
        model = Usuario
        fields = ("rut", "nombre", "email", "password", "rol", "activo")

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def validate_rut(self, value):
        return validar_rut_chileno(value)

    def create(self, validated_data):
        password = validated_data.pop("password")
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario


class ConductorRegistroSerializer(serializers.Serializer):
    """
    Registro de conductor por ADMIN.
    Requiere: RUT del usuario, Folio CONATACOCH, Patente del vehiculo.
    """

    usuario_id = serializers.IntegerField(required=True)
    folio_conatacoch = serializers.CharField(max_length=20, required=True)
    patente = serializers.CharField(max_length=10, required=True)
    cupos_disponibles = serializers.IntegerField(default=0, min_value=0, max_value=30)

    def validate_usuario_id(self, value):
        try:
            usuario = Usuario.objects.get(id=value)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado.")
        if usuario.rol != Usuario.Rol.CONDUCTOR:
            raise serializers.ValidationError("El usuario debe tener rol CONDUCTOR.")
        if hasattr(usuario, "conductor"):
            raise serializers.ValidationError("Este usuario ya es conductor.")
        return value

    def validate_patente(self, value):
        return validar_patente_chilena(value)


# -----------------------------------------------------------------------------
# Telemetria
# -----------------------------------------------------------------------------
class TelemetriaEnviarSerializer(serializers.Serializer):
    """
    Datos de envio de GPS por conductor.
    Se sanitizan contra inyeccion NoSQL antes de guardar en MongoDB.
    """

    latitud = serializers.FloatField(required=True, min_value=-90, max_value=90)
    longitud = serializers.FloatField(required=True, min_value=-180, max_value=180)
    velocidad_kmh = serializers.FloatField(required=True, min_value=0, max_value=250)
    rumbo = serializers.FloatField(required=True, min_value=0, max_value=360)
    cupos_disponibles = serializers.IntegerField(required=True, min_value=0, max_value=30)
    timestamp = serializers.DateTimeField(required=False)


# -----------------------------------------------------------------------------
# Cupos
# -----------------------------------------------------------------------------
class CambioCuposSerializer(serializers.Serializer):
    cupos_disponibles = serializers.IntegerField(required=True, min_value=0, max_value=30)


# -----------------------------------------------------------------------------
# Pago QR
# -----------------------------------------------------------------------------
class PagoQRSerializer(serializers.Serializer):
    """
    Solicitud de pago con QR por pasajero.
    Crea TransaccionPago PENDIENTE y retorna codigo QR.
    """

    conductor_id = serializers.IntegerField(required=True)
    linea_id = serializers.IntegerField(required=True)
    monto = serializers.DecimalField(required=True, max_digits=12, decimal_places=2, min_value=0)


class PagoConfirmarSerializer(serializers.Serializer):
    """
    Confirmacion de pago por conductor.
    Valida que el QR exista, este PENDIENTE y pertenezca al conductor autenticado.
    """

    codigo_qr_uuid = serializers.UUIDField(required=True)


# -----------------------------------------------------------------------------
# ETA para pasajeros
# -----------------------------------------------------------------------------
class ETACalcularSerializer(serializers.Serializer):
    """
    Calculo de tiempo estimado de llegada para un pasajero.
    """

    linea_id = serializers.IntegerField(required=True)
    latitud_pasajero = serializers.FloatField(required=True, min_value=-90, max_value=90)
    longitud_pasajero = serializers.FloatField(required=True, min_value=-180, max_value=180)
