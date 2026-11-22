"""Serializers de solo lectura para la API de Fase 1."""
from __future__ import annotations

from rest_framework import serializers

from core.models import (
    Conductor,
    LineaColectiva,
    Paradero,
    TransaccionPago,
    Usuario,
    Vehiculo,
)


class UsuarioSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "rut",
            "nombre",
            "email",
            "rol",
            "rol_display",
            "activo",
            "intentos_fallidos",
            "bloqueado_hasta",
            "date_joined",
        )
        read_only_fields = fields


class LineaColectivaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaColectiva
        fields = (
            "id",
            "region",
            "folio",
            "tipo_servicio",
            "nombre_recorrido",
            "tipo_trazado",
            "nombre_origen",
            "comuna_origen",
            "domicilio_origen",
            "nombre_destino",
            "comuna_destino",
            "domicilio_destino",
            "tarifa_actual",
        )
        read_only_fields = fields


class VehiculoSerializer(serializers.ModelSerializer):
    linea_folio = serializers.IntegerField(source="linea.folio", read_only=True)
    linea_recorrido = serializers.CharField(source="linea.nombre_recorrido", read_only=True)

    class Meta:
        model = Vehiculo
        fields = (
            "id",
            "patente",
            "marca_modelo",
            "capacidad_pasajeros",
            "linea",
            "linea_folio",
            "linea_recorrido",
        )
        read_only_fields = fields


class ConductorSerializer(serializers.ModelSerializer):
    usuario_rut = serializers.CharField(source="usuario.rut", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.nombre", read_only=True)
    patente = serializers.CharField(source="vehiculo.patente", read_only=True)
    linea_folio = serializers.IntegerField(source="vehiculo.linea.folio", read_only=True)

    class Meta:
        model = Conductor
        # otp_secreto y token_sesion_activa NUNCA se exponen.
        fields = (
            "id",
            "usuario",
            "usuario_rut",
            "usuario_nombre",
            "folio_conatacoch",
            "vehiculo",
            "patente",
            "linea_folio",
            "en_turno",
            "cupos_disponibles",
        )
        read_only_fields = fields


class ParaderoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paradero
        fields = ("id", "nombre", "comuna", "latitud", "longitud", "linea")
        read_only_fields = fields


class TransaccionPagoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    pasajero_rut = serializers.CharField(source="pasajero.rut", read_only=True)
    conductor_folio = serializers.CharField(source="conductor.folio_conatacoch", read_only=True)
    linea_folio = serializers.IntegerField(source="linea.folio", read_only=True)

    class Meta:
        model = TransaccionPago
        fields = (
            "id",
            "codigo_qr_uuid",
            "pasajero",
            "pasajero_rut",
            "conductor",
            "conductor_folio",
            "linea",
            "linea_folio",
            "monto",
            "fecha_hora",
            "estado",
            "estado_display",
        )
        read_only_fields = fields
