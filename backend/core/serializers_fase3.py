"""
Serializers de apoyo para la Fase 3 (web mobile-first y app Android).

Este modulo es aditivo: no reemplaza ni modifica los serializers de Fase 2.
Expone contratos de escritura para el CRUD administrativo de conductores y
lineas, reutilizando los validadores chilenos ya probados.
"""
from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.models import Conductor, Cliente, LineaColectiva, Usuario, Vehiculo
from core.serializers_fase2 import validar_patente_chilena, validar_rut_chileno


class ConductorAdminCreateSerializer(serializers.Serializer):
    """Alta completa de un conductor: usuario + vehiculo + perfil.

    El endpoint de Fase 2 exige un ``usuario_id`` ya existente. Para que el
    panel administrativo pueda operar sin pasar por Django Admin, este
    serializer crea las tres entidades en una sola transaccion.
    """

    rut = serializers.CharField(max_length=12)
    nombre = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, min_length=8)
    folio_conatacoch = serializers.CharField(max_length=20)
    patente = serializers.CharField(max_length=10)
    linea_id = serializers.IntegerField(min_value=1)
    cupos_disponibles = serializers.IntegerField(default=0, min_value=0, max_value=30)
    marca_modelo = serializers.CharField(max_length=120, required=False, default="Por definir")
    capacidad_pasajeros = serializers.IntegerField(
        required=False, default=4, min_value=1, max_value=30
    )

    def validate_rut(self, value: str) -> str:
        rut = validar_rut_chileno(value)
        if Usuario.objects.filter(rut=rut).exists():
            raise serializers.ValidationError("Ya existe un usuario con este RUT.")
        return rut

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return email

    def validate_folio_conatacoch(self, value: str) -> str:
        folio = value.strip()
        if not folio:
            raise serializers.ValidationError("El folio CONATACOCH es obligatorio.")
        if Conductor.objects.filter(folio_conatacoch=folio).exists():
            raise serializers.ValidationError("Ya existe un conductor con este folio.")
        return folio

    def validate_patente(self, value: str) -> str:
        return validar_patente_chilena(value)

    def validate_linea_id(self, value: int) -> int:
        if not LineaColectiva.objects.filter(pk=value).exists():
            raise serializers.ValidationError("La linea indicada no existe.")
        return value

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data: dict) -> Conductor:
        from django.db import transaction

        with transaction.atomic():
            usuario = Usuario(
                rut=validated_data["rut"],
                nombre=validated_data["nombre"],
                email=validated_data["email"],
                rol=Usuario.Rol.CONDUCTOR,
                activo=True,
            )
            usuario.set_password(validated_data["password"])
            usuario.save()

            vehiculo, _ = Vehiculo.objects.update_or_create(
                patente=validated_data["patente"],
                defaults={
                    "marca_modelo": validated_data.get("marca_modelo") or "Por definir",
                    "capacidad_pasajeros": validated_data.get("capacidad_pasajeros", 4),
                    "linea_id": validated_data["linea_id"],
                },
            )

            return Conductor.objects.create(
                usuario=usuario,
                folio_conatacoch=validated_data["folio_conatacoch"],
                vehiculo=vehiculo,
                cupos_disponibles=validated_data.get("cupos_disponibles", 0),
                en_turno=False,
            )


class ConductorAdminUpdateSerializer(serializers.Serializer):
    """Actualizacion parcial del perfil de conductor y su vehiculo."""

    folio_conatacoch = serializers.CharField(max_length=20, required=False)
    patente = serializers.CharField(max_length=10, required=False)
    linea_id = serializers.IntegerField(min_value=1, required=False)
    cupos_disponibles = serializers.IntegerField(
        min_value=0, max_value=30, required=False
    )
    en_turno = serializers.BooleanField(required=False)
    marca_modelo = serializers.CharField(max_length=120, required=False)
    capacidad_pasajeros = serializers.IntegerField(
        min_value=1, max_value=30, required=False
    )

    def validate_folio_conatacoch(self, value: str) -> str:
        folio = value.strip()
        if not folio:
            raise serializers.ValidationError("El folio CONATACOCH es obligatorio.")
        conductor = self.context.get("conductor")
        qs = Conductor.objects.filter(folio_conatacoch=folio)
        if conductor is not None:
            qs = qs.exclude(pk=conductor.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe otro conductor con este folio.")
        return folio

    def validate_patente(self, value: str) -> str:
        return validar_patente_chilena(value)

    def validate_linea_id(self, value: int) -> int:
        if not LineaColectiva.objects.filter(pk=value).exists():
            raise serializers.ValidationError("La linea indicada no existe.")
        return value

    def update(self, instance: Conductor, validated_data: dict) -> Conductor:
        from django.db import transaction

        with transaction.atomic():
            for campo in ("folio_conatacoch", "cupos_disponibles", "en_turno"):
                if campo in validated_data:
                    setattr(instance, campo, validated_data[campo])

            if "cupos_disponibles" in validated_data and not validated_data.get(
                "en_turno", instance.en_turno
            ):
                # Un conductor fuera de turno no puede ofrecer cupos.
                instance.cupos_disponibles = 0

            instance.save()

            vehiculo = instance.vehiculo
            actualizar_vehiculo = False
            for campo in ("patente", "marca_modelo", "capacidad_pasajeros"):
                if campo in validated_data:
                    setattr(vehiculo, campo, validated_data[campo])
                    actualizar_vehiculo = True
            if "linea_id" in validated_data:
                vehiculo.linea_id = validated_data["linea_id"]
                actualizar_vehiculo = True
            if actualizar_vehiculo:
                vehiculo.save()

            return instance


class RegistroClienteSerializer(serializers.Serializer):
    """Auto-registro publico de pasajeros (rol CLIENTE).

    El registro de conductores sigue siendo exclusivo del ADMIN porque exige
    validar RUT, folio y patente. Este endpoint permite que un pasajero cree
    su propia cuenta sin escalar privilegios: el rol siempre es CLIENTE.
    """

    rut = serializers.CharField(max_length=12)
    nombre = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    telefono = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=""
    )
    comuna = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    direccion = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate_rut(self, value: str) -> str:
        rut = validar_rut_chileno(value)
        if Usuario.objects.filter(rut=rut).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este RUT.")
        return rut

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este email.")
        return email

    def validate(self, attrs: dict) -> dict:
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        # validate_password aplica la politica de settings (minimo 12,
        # no numerica, no comun y no similar a los datos del usuario).
        candidato = Usuario(
            rut=attrs.get("rut", ""),
            nombre=attrs.get("nombre", ""),
            email=attrs.get("email", ""),
        )
        try:
            validate_password(attrs["password"], user=candidato)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data: dict) -> Usuario:
        from django.db import transaction

        validated_data.pop("password_confirm", None)
        perfil = {
            "telefono": validated_data.pop("telefono", ""),
            "comuna": validated_data.pop("comuna", ""),
            "direccion": validated_data.pop("direccion", ""),
        }
        password = validated_data.pop("password")
        with transaction.atomic():
            usuario = Usuario(
                rut=validated_data["rut"],
                nombre=validated_data["nombre"],
                email=validated_data["email"],
                rol=Usuario.Rol.CLIENTE,
                activo=True,
            )
            usuario.set_password(password)
            usuario.save()
            Cliente.objects.get_or_create(usuario=usuario, defaults=perfil)
        return usuario


class LineaUpsertSerializer(serializers.Serializer):
    """Alta/actualizacion idempotente de una linea colectiva."""

    region = serializers.IntegerField(min_value=1, max_value=16)
    folio = serializers.IntegerField(min_value=1)
    tipo_servicio = serializers.CharField(max_length=80)
    nombre_recorrido = serializers.CharField(max_length=50)
    tipo_trazado = serializers.ChoiceField(
        choices=LineaColectiva.TipoTrazado.choices,
        default=LineaColectiva.TipoTrazado.PRINCIPAL,
    )
    nombre_origen = serializers.CharField(max_length=150)
    comuna_origen = serializers.CharField(max_length=100)
    domicilio_origen = serializers.CharField(max_length=200)
    nombre_destino = serializers.CharField(max_length=150)
    comuna_destino = serializers.CharField(max_length=100)
    domicilio_destino = serializers.CharField(max_length=200)
    tarifa_actual = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, default=0
    )

    def validate_tipo_servicio(self, value: str) -> str:
        valor = value.strip().upper()
        if not valor:
            raise serializers.ValidationError("El tipo de servicio es obligatorio.")
        return valor
