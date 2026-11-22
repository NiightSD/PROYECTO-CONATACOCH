"""
Vistas aditivas de la Fase 3.

No reemplazan la logica validada de Fase 2. Cubren tres necesidades que la
web mobile-first y la app Android requieren y que no tenian endpoint propio:

  * GET  /api/telemetria/flota/          - ultima posicion de la flota en turno.
  * GET  /api/conductor/perfil/          - perfil del conductor autenticado.
  * POST /api/conductor/finalizar-turno/ - cierre de turno con OTP (2FA).
  * POST /api/admin-api/conductores/completo/ - alta usuario+vehiculo+conductor.
  * PATCH/DELETE /api/admin-api/conductores/<id>/ - edicion/baja administrativa.
  * POST /api/admin-api/lineas/upsert/   - alta/actualizacion idempotente de linea.

Todos los permisos se apoyan en las clases RBAC ya probadas de Fase 2.
"""
from __future__ import annotations

import logging
from datetime import timedelta, timezone as dt_timezone

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core import mongo
from core.models import Conductor, LineaColectiva, Usuario
from core.permissions import EsAdmin, EsConductor
from core.security import generar_codigo_otp, verificar_codigo_otp
from core.serializers import ConductorSerializer, LineaColectivaSerializer
from core.serializers_fase3 import (
    ConductorAdminCreateSerializer,
    ConductorAdminUpdateSerializer,
    LineaUpsertSerializer,
)

logger = logging.getLogger("core.views_fase3")


def _iso_timestamp(valor):
    """Serializa timestamps de Mongo/Django de forma segura."""
    if valor is None:
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


def _edad_segundos(valor) -> int | None:
    if valor is None or not hasattr(valor, "timestamp"):
        return None
    if timezone.is_naive(valor):
        valor = valor.replace(tzinfo=dt_timezone.utc)
    return max(0, int((timezone.now() - valor).total_seconds()))


# =============================================================================
# FLOTA EN VIVO
# =============================================================================
class FlotaEnVivoView(APIView):
    """Ultima posicion conocida de cada conductor en turno.

    Es una lectura de apoyo para mapas de pasajero y administracion. La fuente
    de verdad sigue siendo MongoDB (``telemetria_ubicacion``); aqui solo se
    proyecta el ultimo documento de cada vehiculo.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Flota"], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        linea_id = request.query_params.get("linea_id")
        conductores = (
            Conductor.objects.select_related("usuario", "vehiculo", "vehiculo__linea")
            .filter(en_turno=True)
            .order_by("folio_conatacoch")
        )

        if linea_id:
            if not str(linea_id).isdigit():
                return Response(
                    {
                        "error": "parametro_invalido",
                        "detail": "linea_id debe ser numerico.",
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not LineaColectiva.objects.filter(pk=int(linea_id)).exists():
                return Response(
                    {
                        "error": "linea_no_encontrada",
                        "detail": "La linea indicada no existe.",
                        "status_code": status.HTTP_404_NOT_FOUND,
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            conductores = conductores.filter(vehiculo__linea_id=int(linea_id))

        coleccion = mongo.get_collection()
        vehiculos: list[dict] = []

        for conductor in conductores[:500]:
            ultimo = (
                coleccion.find({"id_vehiculo": conductor.vehiculo_id})
                .sort("timestamp", -1)
                .limit(1)
            )
            doc = next(ultimo, None)
            if not doc:
                continue
            coords = (doc.get("ubicacion") or {}).get("coordinates") or []
            if len(coords) != 2:
                continue
            longitud, latitud = coords[0], coords[1]
            vehiculos.append(
                {
                    "conductor_id": conductor.id,
                    "id_vehiculo": conductor.vehiculo_id,
                    "folio_conatacoch": conductor.folio_conatacoch,
                    "usuario_nombre": conductor.usuario.nombre,
                    "patente": conductor.vehiculo.patente,
                    "linea_id": conductor.vehiculo.linea_id,
                    "linea_folio": conductor.vehiculo.linea.folio,
                    "linea_nombre": conductor.vehiculo.linea.nombre_recorrido,
                    "cupos_disponibles": conductor.cupos_disponibles,
                    "latitud": float(latitud),
                    "longitud": float(longitud),
                    "velocidad_kmh": float(doc.get("velocidad_kmh", 0) or 0),
                    "rumbo": float(doc.get("rumbo", 0) or 0),
                    "timestamp": _iso_timestamp(doc.get("timestamp")),
                    "edad_segundos": _edad_segundos(doc.get("timestamp")),
                }
            )

        return Response(
            {
                "total": len(vehiculos),
                "linea_id": int(linea_id) if linea_id else None,
                "vehiculos": vehiculos,
                "timestamp": timezone.now().isoformat(),
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# CONDUCTOR - PERFIL Y CIERRE DE TURNO
# =============================================================================
class ConductorPerfilView(APIView):
    """Perfil operativo del conductor autenticado (sin secretos OTP)."""

    permission_classes = [EsConductor]

    @extend_schema(tags=["Conductor - Turno"], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        try:
            conductor = Conductor.objects.select_related(
                "usuario", "vehiculo", "vehiculo__linea"
            ).get(usuario=request.user)
        except Conductor.DoesNotExist:
            return Response(
                {
                    "error": "sin_perfil_conductor",
                    "detail": "El usuario no tiene perfil de conductor.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "id": conductor.id,
                "usuario_id": conductor.usuario_id,
                "usuario_nombre": conductor.usuario.nombre,
                "usuario_email": conductor.usuario.email,
                "usuario_rut": conductor.usuario.rut,
                "folio_conatacoch": conductor.folio_conatacoch,
                "patente": conductor.vehiculo.patente,
                "marca_modelo": conductor.vehiculo.marca_modelo,
                "capacidad_pasajeros": conductor.vehiculo.capacidad_pasajeros,
                "linea_id": conductor.vehiculo.linea_id,
                "linea_folio": conductor.vehiculo.linea.folio,
                "linea_nombre": conductor.vehiculo.linea.nombre_recorrido,
                "en_turno": conductor.en_turno,
                "cupos_disponibles": conductor.cupos_disponibles,
                "otp_pendiente": bool(conductor.otp_codigo),
            },
            status=status.HTTP_200_OK,
        )


class ConductorFinalizarTurnoView(APIView):
    """Cierre de turno con confirmacion OTP (2FA).

    Flujo equivalente al inicio de turno:
      1. ``{"solicitar_codigo": true}`` genera un OTP temporal.
      2. ``{"codigo_otp": "123456"}`` valida y cierra el turno.
    """

    permission_classes = [EsConductor]

    @extend_schema(tags=["Conductor - Turno"], request=OpenApiTypes.OBJECT)
    def post(self, request):
        try:
            conductor = Conductor.objects.select_related("vehiculo").get(
                usuario=request.user
            )
        except Conductor.DoesNotExist:
            return Response(
                {
                    "error": "sin_perfil_conductor",
                    "detail": "El usuario no tiene perfil de conductor.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not conductor.en_turno:
            return Response(
                {
                    "estado": "turno_inactivo",
                    "detail": "El conductor no tiene un turno activo.",
                    "en_turno": False,
                },
                status=status.HTTP_200_OK,
            )

        codigo_entrado = request.data.get("codigo_otp")
        solicitar_codigo = request.data.get("solicitar_codigo", False)

        if solicitar_codigo or not codigo_entrado:
            codigo = generar_codigo_otp()
            conductor.otp_codigo = codigo
            conductor.otp_codigo_expira = timezone.now() + timedelta(
                minutes=settings.OTP_EXPIRACION_MINUTOS
            )
            conductor.save(update_fields=["otp_codigo", "otp_codigo_expira"])
            logger.info(
                "OTP de cierre generado para conductor %s", conductor.folio_conatacoch
            )
            return Response(
                {
                    "estado": "otp_requerido",
                    "detail": "Se requiere codigo OTP para finalizar turno.",
                    "codigo_otp": codigo,
                    "expires_in_minutes": settings.OTP_EXPIRACION_MINUTOS,
                },
                status=status.HTTP_200_OK,
            )

        if not conductor.otp_codigo or not conductor.otp_codigo_expira:
            return Response(
                {
                    "error": "otp_no_solicitado",
                    "detail": "Primero solicite el codigo OTP.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if conductor.otp_codigo_expira <= timezone.now():
            conductor.otp_codigo = ""
            conductor.otp_codigo_expira = None
            conductor.save(update_fields=["otp_codigo", "otp_codigo_expira"])
            return Response(
                {
                    "error": "otp_expirado",
                    "detail": "El codigo OTP ha expirado. Solicite uno nuevo.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verificar_codigo_otp(codigo_entrado, conductor.otp_codigo):
            return Response(
                {
                    "error": "otp_invalido",
                    "detail": "Codigo OTP incorrecto.",
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        conductor.en_turno = False
        conductor.cupos_disponibles = 0
        conductor.otp_codigo = ""
        conductor.otp_codigo_expira = None
        conductor.clear_token_sesion()
        conductor.save(
            update_fields=[
                "en_turno",
                "cupos_disponibles",
                "otp_codigo",
                "otp_codigo_expira",
                "token_sesion_activa",
            ]
        )
        logger.info("Turno finalizado: %s", conductor.folio_conatacoch)

        return Response(
            {
                "estado": "turno_finalizado",
                "conductor": conductor.folio_conatacoch,
                "patente": conductor.vehiculo.patente,
                "en_turno": False,
                "cupos_disponibles": 0,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# ADMIN - ALTA/EDICION DE CONDUCTORES Y LINEAS
# =============================================================================
class AdminConductorCreateCompletoView(APIView):
    """Alta transaccional de usuario CONDUCTOR + vehiculo + perfil."""

    permission_classes = [EsAdmin]

    @extend_schema(tags=["Admin - Conductores"], request=ConductorAdminCreateSerializer)
    def post(self, request):
        serializer = ConductorAdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conductor = serializer.save()
        except IntegrityError as exc:
            logger.warning("Alta de conductor rechazada por integridad: %s", exc)
            return Response(
                {
                    "error": "conflicto_integridad",
                    "detail": "El RUT, email, patente o folio ya existen.",
                    "status_code": status.HTTP_409_CONFLICT,
                },
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as exc:  # pragma: no cover - defensa ante fallos inesperados
            logger.error("Error creando conductor completo: %s", exc, exc_info=True)
            return Response(
                {
                    "error": "error_registro_conductor",
                    "detail": "No se pudo registrar el conductor.",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        datos = ConductorSerializer(conductor).data
        datos["usuario_email"] = conductor.usuario.email
        datos["usuario_rut"] = conductor.usuario.rut
        return Response(datos, status=status.HTTP_201_CREATED)


class AdminConductorDetailView(APIView):
    """Lectura, edicion y baja de un conductor (solo ADMIN)."""

    permission_classes = [EsAdmin]

    def _obtener(self, pk: int) -> Conductor:
        return Conductor.objects.select_related(
            "usuario", "vehiculo", "vehiculo__linea"
        ).get(pk=pk)

    @extend_schema(tags=["Admin - Conductores"], responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk: int):
        try:
            conductor = self._obtener(pk)
        except Conductor.DoesNotExist:
            return Response(
                {
                    "error": "conductor_no_encontrado",
                    "detail": "El conductor no existe.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ConductorSerializer(conductor).data)

    @extend_schema(tags=["Admin - Conductores"], request=ConductorAdminUpdateSerializer)
    def patch(self, request, pk: int):
        try:
            conductor = self._obtener(pk)
        except Conductor.DoesNotExist:
            return Response(
                {
                    "error": "conductor_no_encontrado",
                    "detail": "El conductor no existe.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConductorAdminUpdateSerializer(
            conductor, data=request.data, partial=True, context={"conductor": conductor}
        )
        serializer.is_valid(raise_exception=True)
        try:
            conductor = serializer.save()
        except IntegrityError:
            return Response(
                {
                    "error": "conflicto_integridad",
                    "detail": "La patente o el folio ya estan en uso.",
                    "status_code": status.HTTP_409_CONFLICT,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ConductorSerializer(conductor).data)

    @extend_schema(tags=["Admin - Conductores"])
    def delete(self, request, pk: int):
        try:
            conductor = self._obtener(pk)
        except Conductor.DoesNotExist:
            return Response(
                {
                    "error": "conductor_no_encontrado",
                    "detail": "El conductor no existe.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            with transaction.atomic():
                conductor.delete()
        except ProtectedError:
            return Response(
                {
                    "error": "conductor_con_transacciones",
                    "detail": (
                        "No se puede eliminar: el conductor tiene pagos asociados. "
                        "Desactívelo o cierre su turno."
                    ),
                    "status_code": status.HTTP_409_CONFLICT,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminLineaUpsertView(APIView):
    """Alta/actualizacion idempotente de una linea (solo ADMIN)."""

    permission_classes = [EsAdmin]

    @extend_schema(tags=["Admin - Lineas"], request=LineaUpsertSerializer)
    def post(self, request):
        serializer = LineaUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        with transaction.atomic():
            linea, creada = LineaColectiva.objects.update_or_create(
                folio=datos["folio"],
                nombre_recorrido=datos["nombre_recorrido"],
                tipo_trazado=datos["tipo_trazado"],
                defaults={
                    "region": datos["region"],
                    "tipo_servicio": datos["tipo_servicio"],
                    "nombre_origen": datos["nombre_origen"],
                    "comuna_origen": datos["comuna_origen"],
                    "domicilio_origen": datos["domicilio_origen"],
                    "nombre_destino": datos["nombre_destino"],
                    "comuna_destino": datos["comuna_destino"],
                    "domicilio_destino": datos["domicilio_destino"],
                    "tarifa_actual": datos["tarifa_actual"],
                },
            )

        return Response(
            LineaColectivaSerializer(linea).data,
            status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK,
        )
