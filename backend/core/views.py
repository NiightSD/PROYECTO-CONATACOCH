"""Vistas de la API de Fase 1: salud, metricas y consulta del dominio."""
from __future__ import annotations

import logging
import time

from django.conf import settings
from django.db import connections
from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core import mongo
from core.models import (
    Conductor,
    LineaColectiva,
    Paradero,
    TransaccionPago,
    Usuario,
    Vehiculo,
)
from core.serializers import (
    ConductorSerializer,
    LineaColectivaSerializer,
    ParaderoSerializer,
    TransaccionPagoSerializer,
    VehiculoSerializer,
)

logger = logging.getLogger("core.views")


def _parse_fecha(valor: str):
    """Parsea ISO-8601 y garantiza datetime con zona horaria (UTC por defecto)."""
    fecha = parse_datetime(valor)
    if fecha and timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha)
    return fecha


# -----------------------------------------------------------------------------
# Salud
# -----------------------------------------------------------------------------
class HealthLiveView(APIView):
    """Liveness: solo confirma que el proceso responde (sin tocar dependencias)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["Salud"], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "conatacoch-backend",
                "version": "1.0.0-fase1",
                "timestamp": timezone.now().isoformat(),
            }
        )


class HealthView(APIView):
    """Readiness: verifica MySQL y MongoDB Atlas/fallback."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["Salud"], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        componentes: dict = {}

        inicio = time.perf_counter()
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            componentes["mysql"] = {
                "status": "ok",
                "latency_ms": round((time.perf_counter() - inicio) * 1000, 2),
                "database": settings.DATABASES["default"]["NAME"],
            }
            mysql_ok = True
        except Exception as exc:
            logger.exception("Healthcheck MySQL fallo")
            componentes["mysql"] = {"status": "error", "detail": str(exc)[:200]}
            mysql_ok = False

        mongo_ok, latencia = mongo.ping()
        componentes["mongodb"] = {
            "status": "ok" if mongo_ok else "error",
            "latency_ms": latencia,
            "mode": "atlas" if settings.MONGO_ATLAS_URI else "local",
            "database": settings.MONGO_DB_NAME,
        }

        if mysql_ok and mongo_ok:
            estado = "ok"
            codigo = status.HTTP_200_OK
        elif mysql_ok:
            estado = "degraded"
            codigo = status.HTTP_200_OK
        else:
            estado = "down"
            codigo = status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": estado,
                "service": "conatacoch-backend",
                "version": "1.0.0-fase1",
                "components": componentes,
                "timestamp": timezone.now().isoformat(),
            },
            status=codigo,
        )


# -----------------------------------------------------------------------------
# Metricas publicas (solo agregados, sin datos personales)
# -----------------------------------------------------------------------------
class StatsView(APIView):
    """Resumen agregado usado por el panel web (no expone PII)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["Salud"], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        lineas = LineaColectiva.objects.aggregate(
            total=Count("id"),
            tarifa_promedio=Avg("tarifa_actual"),
        )
        comunas = set(
            LineaColectiva.objects.values_list("comuna_origen", flat=True).distinct()
        ) | set(
            LineaColectiva.objects.values_list("comuna_destino", flat=True).distinct()
        )

        return Response(
            {
                "lineas": lineas["total"] or 0,
                "folios": LineaColectiva.objects.values("folio").distinct().count(),
                "comunas": len({c for c in comunas if c}),
                "paraderos": Paradero.objects.count(),
                "vehiculos": Vehiculo.objects.count(),
                "conductores": Conductor.objects.count(),
                "conductores_en_turno": Conductor.objects.filter(en_turno=True).count(),
                "pasajeros": Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).count(),
                "transacciones": TransaccionPago.objects.count(),
                "tarifa_promedio": round(float(lineas["tarifa_promedio"] or 0), 2),
                "timestamp": timezone.now().isoformat(),
            }
        )


# -----------------------------------------------------------------------------
# ViewSets de dominio
# -----------------------------------------------------------------------------
@extend_schema_view(
    list=extend_schema(tags=["Lineas"]),
    retrieve=extend_schema(tags=["Lineas"]),
)
class LineaColectivaViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalogo publico de recorridos. Soporta filtros por comuna, folio y region."""

    serializer_class = LineaColectivaSerializer
    permission_classes = [AllowAny]
    search_fields = ["nombre_recorrido", "comuna_origen", "comuna_destino", "tipo_servicio"]
    ordering_fields = ["folio", "region", "tarifa_actual", "comuna_origen"]
    ordering = ["folio", "nombre_recorrido"]

    def get_queryset(self):
        queryset = LineaColectiva.objects.all()
        params = self.request.query_params

        comuna = params.get("comuna")
        if comuna:
            queryset = queryset.filter(
                Q(comuna_origen__iexact=comuna) | Q(comuna_destino__iexact=comuna)
            )

        folio = params.get("folio")
        if folio and folio.isdigit():
            queryset = queryset.filter(folio=int(folio))

        region = params.get("region")
        if region and region.isdigit():
            queryset = queryset.filter(region=int(region))

        tipo = params.get("tipo_servicio")
        if tipo:
            queryset = queryset.filter(tipo_servicio__icontains=tipo)

        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Paraderos"]),
    retrieve=extend_schema(tags=["Paraderos"]),
)
class ParaderoViewSet(viewsets.ReadOnlyModelViewSet):
    """Paraderos base georreferenciados (consulta publica)."""

    serializer_class = ParaderoSerializer
    permission_classes = [AllowAny]
    search_fields = ["nombre", "comuna"]
    ordering_fields = ["comuna", "nombre"]
    ordering = ["comuna", "nombre"]

    def get_queryset(self):
        queryset = Paradero.objects.all()
        comuna = self.request.query_params.get("comuna")
        if comuna:
            queryset = queryset.filter(comuna__iexact=comuna)
        linea = self.request.query_params.get("linea")
        if linea and str(linea).isdigit():
            queryset = queryset.filter(linea_id=int(linea))
        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Flota"]),
    retrieve=extend_schema(tags=["Flota"]),
)
class VehiculoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VehiculoSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["patente", "marca_modelo"]
    ordering = ["patente"]

    def get_queryset(self):
        queryset = Vehiculo.objects.select_related("linea")
        linea = self.request.query_params.get("linea")
        if linea and str(linea).isdigit():
            queryset = queryset.filter(linea_id=int(linea))
        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Flota"]),
    retrieve=extend_schema(tags=["Flota"]),
)
class ConductorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConductorSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["folio_conatacoch", "usuario__rut", "usuario__email", "vehiculo__patente"]
    ordering = ["folio_conatacoch"]

    def get_queryset(self):
        queryset = Conductor.objects.select_related("usuario", "vehiculo", "vehiculo__linea")
        en_turno = self.request.query_params.get("en_turno")
        if en_turno is not None:
            queryset = queryset.filter(en_turno=en_turno.lower() in {"1", "true", "si"})
        folio = self.request.query_params.get("folio")
        if folio:
            queryset = queryset.filter(folio_conatacoch=folio)
        return queryset


@extend_schema_view(
    list=extend_schema(tags=["Pagos"]),
    retrieve=extend_schema(tags=["Pagos"]),
)
class TransaccionPagoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransaccionPagoSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["codigo_qr_uuid", "pasajero__rut", "conductor__folio_conatacoch"]
    ordering_fields = ["fecha_hora", "monto"]
    ordering = ["-fecha_hora"]

    def get_queryset(self):
        queryset = TransaccionPago.objects.select_related(
            "pasajero", "conductor", "linea"
        )
        params = self.request.query_params

        estado = params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado.upper())

        for campo in ("conductor", "linea", "pasajero"):
            valor = params.get(campo)
            if valor and str(valor).isdigit():
                queryset = queryset.filter(**{f"{campo}_id": int(valor)})

        desde = params.get("desde")
        if desde:
            fecha = _parse_fecha(desde)
            if fecha:
                queryset = queryset.filter(fecha_hora__gte=fecha)
        hasta = params.get("hasta")
        if hasta:
            fecha = _parse_fecha(hasta)
            if fecha:
                queryset = queryset.filter(fecha_hora__lte=fecha)

        return queryset
