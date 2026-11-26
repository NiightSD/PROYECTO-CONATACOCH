"""
Vistas de Fase 2 - Logica de negocio segura de CONATACOCH.

Endpoints implementados (OWASP Top 10 aplicado):
  * POST   /api/auth/login/        - Login con Argon2id + anti-fuerza bruta.
  * POST   /api/auth/refresh/      - Refresh de JWT (simplejwt).
  * POST   /api/admin/conductores/ - Registro de conductor (solo ADMIN).
  * GET    /api/admin/conductores/ - Listado paginado de conductores (ADMIN).
  * POST   /api/admin/lineas/      - Crear/actualizar linea (ADMIN).
  * POST   /api/admin/tarifas/     - Actualizar tarifa de linea (ADMIN).
  * GET    /api/lineas/            - Consulta publica de rutas (ya existe).
  * GET    /api/paraderos/         - Consulta publica de paraderos (ya existe).
  * GET    /api/eta/calcular/      - Calculo de ETA para pasajeros (CLIENTE).
  * POST   /api/telemetria/enviar/ - Envío de GPS con anti-spoofing (CONDUCTOR).
  * POST   /api/conductor/iniciar-turno/ - Inicio de turno con 2FA (CONDUCTOR).
  * POST   /api/conductor/cupos/   - Cambio de cupos disponibles (CONDUCTOR).
  * POST   /api/pagos/qr/          - Generar pago QR (CLIENTE).
  * POST   /api/pagos/confirmar/   - Confirmar pago QR (CONDUCTOR).
"""
from __future__ import annotations

import hashlib
import logging
import math
import time
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core import mongo
from core.mongo import insertar_ubicacion
from core.models import (
    Conductor,
    LineaColectiva,
    Paradero,
    TransaccionPago,
    Usuario,
    Vehiculo,
)
from core.pagination import StandardResultsSetPagination
from core.permissions import (
    PuedeIniciarTurno,
    EsAdmin,
    EsCliente,
    EsConductor,
    EsAdminOPropietarioRecurso,
)
from core.security import (
    hash_password_argon2id,
    verify_password_argon2id,
    needs_argon2_rehash,
    usuario_esta_bloqueado,
    registrar_intento_fallido,
    registrar_exito,
    sanitizar_para_mongo,
    validar_documento_mongo,
    haversine_km,
    calcular_velocidad_kmh,
    es_velocidad_sospechosa,
    VELOCIDAD_MAXIMA_KMH,
    hash_token_sesion,
    generar_codigo_otp,
    verificar_codigo_otp,
    custom_exception_handler,
)
from core.serializers import (
    ConductorSerializer,
    LineaColectivaSerializer,
    ParaderoSerializer,
    TransaccionPagoSerializer,
    VehiculoSerializer,
)
from core.serializers_fase2 import (
    LoginSerializer,
    UsuarioRegistroSerializer,
    ConductorRegistroSerializer,
    TelemetriaEnviarSerializer,
    CambioCuposSerializer,
    PagoQRSerializer,
    PagoConfirmarSerializer,
    ETACalcularSerializer,
)

logger = logging.getLogger("core.views_fase2")


# =============================================================================
# AUTENTICACION - Login con Argon2id y anti-fuerza bruta (OWASP A07:2021)
# =============================================================================
class AuthLoginView(APIView):
    """
    Autenticacion de usuario con hash Argon2id y proteccion contra fuerza bruta.

    Flujo:
      1. Verifica si el usuario esta bloqueado (intentos >= 5 -> 15 min).
      2. Verifica password con Argon2id (rehash si es necesario).
      3. Si falla, registra intento fallido y bloquea si corresponde.
      4. Si exito, emite access (15 min) + refresh (7 dias) y reinicia contador.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Autenticacion"],
        request=LoginSerializer,
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            # No revelar si el email existe (timing attack mitigado)
            time.sleep(0.3)  # constante de retraso para mitigar enumeracion
            logger.warning("Intento de login con email inexistente: %s", email)
            return Response(
                {
                    "error": "credenciales_invalidas",
                    "detail": "Email o password incorrectos.",
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Bloqueo por fuerza bruta
        if usuario_esta_bloqueado(usuario):
            logger.warning("Intento de login en usuario bloqueado: %s", email)
            return Response(
                {
                    "error": "usuario_bloqueado",
                    "detail": (
                        f"Cuenta bloqueada temporalmente por intentos fallidos. "
                        f"Intente de nuevo despues de {usuario.bloqueado_hasta}."
                    ),
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Verificar password con Argon2id
        password_valida = verify_password_argon2id(password, usuario.password)

        if not password_valida:
            registrar_intento_fallido(usuario)
            logger.warning(
                "Password invalida para %s (intento %d/5).",
                email,
                usuario.intentos_fallidos,
            )
            return Response(
                {
                    "error": "credenciales_invalidas",
                    "detail": "Email o password incorrectos.",
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Login exitoso
        if not usuario.activo:
            return Response(
                {
                    "error": "usuario_inactivo",
                    "detail": "La cuenta esta desactivada.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        registrar_exito(usuario)

        # Rehash si los parametros de Argon2 cambiaron
        if needs_argon2_rehash(usuario.password):
            usuario.password = hash_password_argon2id(password)
            usuario.save(update_fields=["password"])

        refresh = RefreshToken.for_user(usuario)
        logger.info("Login exitoso: %s (rol=%s)", email, usuario.rol)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "usuario": {
                    "id": usuario.id,
                    "rut": usuario.rut,
                    "nombre": usuario.nombre,
                    "email": usuario.email,
                    "rol": usuario.rol,
                },
                "access_expires_in": settings.ACCESS_TOKEN_MINUTES * 60
                if hasattr(settings, "ACCESS_TOKEN_MINUTES")
                else 900,
            },
            status=status.HTTP_200_OK,
        )


class AuthRefreshView(APIView):
    """Refresh de token JWT usando refresh token."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["Autenticacion"])
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {
                    "error": "token_requerido",
                    "detail": "Se requiere el token de refresh.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            refresh = RefreshToken(refresh_token)
            access = refresh.access_token
            return Response(
                {
                    "access": str(access),
                    "access_expires_in": settings.ACCESS_TOKEN_MINUTES * 60
                    if hasattr(settings, "ACCESS_TOKEN_MINUTES")
                    else 900,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.warning("Refresh token invalido: %s", exc)
            return Response(
                {
                    "error": "token_invalido",
                    "detail": "Token de refresh invalido o expirado.",
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )


# =============================================================================
# ADMIN - Gestion de conductores, lineas y tarifas (solo ADMIN)
# =============================================================================
class AdminConductorListView(APIView):
    """Listado paginado de conductores (solo ADMIN)."""

    permission_classes = [EsAdmin]

    @extend_schema(tags=["Admin - Conductores"])
    def get(self, request):
        conductores = (
            Conductor.objects.select_related("usuario", "vehiculo", "vehiculo__linea")
            .all()
            .order_by("folio_conatacoch")
        )
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(conductores, request)
        serializer = ConductorSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminConductorCreateView(APIView):
    """Registro de conductor por ADMIN (RUT + Folio + Patente)."""

    permission_classes = [EsAdmin]

    @extend_schema(
        tags=["Admin - Conductores"],
        request=ConductorRegistroSerializer,
    )
    def post(self, request):
        serializer = ConductorRegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario_id = serializer.validated_data["usuario_id"]
        folio = serializer.validated_data["folio_conatacoch"]
        patente = serializer.validated_data["patente"]
        cupos = serializer.validated_data["cupos_disponibles"]

        try:
            with transaction.atomic():
                usuario = Usuario.objects.get(id=usuario_id)

                # Crear o obtener vehiculo por patente
                vehiculo, creado = Vehiculo.objects.get_or_create(
                    patente=patente,
                    defaults={
                        "marca_modelo": "Por definir",
                        "capacidad_pasajeros": 4,
                        "linea_id": 1,  # Se asignara por el admin
                    },
                )

                conductor = Conductor.objects.create(
                    usuario=usuario,
                    folio_conatacoch=folio,
                    vehiculo=vehiculo,
                    cupos_disponibles=cupos,
                    en_turno=False,
                )

                logger.info(
                    "Conductor registrado por ADMIN: folio=%s patente=%s usuario=%s",
                    folio,
                    patente,
                    usuario.email,
                )

                return Response(
                    {
                        "id": conductor.id,
                        "folio_conatacoch": conductor.folio_conatacoch,
                        "patente": vehiculo.patente,
                        "usuario": usuario.email,
                        "cupos_disponibles": conductor.cupos_disponibles,
                    },
                    status=status.HTTP_201_CREATED,
                )
        except Exception as exc:
            logger.error("Error registrando conductor: %s", exc, exc_info=True)
            return Response(
                {
                    "error": "error_registro_conductor",
                    "detail": "No se pudo registrar el conductor.",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminLineaView(APIView):
    """Crear/actualizar linea colectiva (solo ADMIN)."""

    permission_classes = [EsAdmin]

    @extend_schema(tags=["Admin - Lineas"])
    def post(self, request):
        serializer = LineaColectivaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        linea = serializer.save()
        logger.info("Linea creada/actualizada: folio=%s", linea.folio)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminTarifaView(APIView):
    """Actualizar tarifa de una linea (solo ADMIN)."""

    permission_classes = [EsAdmin]

    @extend_schema(tags=["Admin - Tarifas"])
    def post(self, request):
        linea_id = request.data.get("linea_id")
        tarifa = request.data.get("tarifa_actual")

        if not linea_id or tarifa is None:
            return Response(
                {
                    "error": "parametros_requeridos",
                    "detail": "Se requieren linea_id y tarifa_actual.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            linea = LineaColectiva.objects.get(id=linea_id)
        except LineaColectiva.DoesNotExist:
            return Response(
                {
                    "error": "linea_no_encontrada",
                    "detail": "La linea especificada no existe.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        linea.tarifa_actual = tarifa
        linea.save(update_fields=["tarifa_actual"])
        logger.info("Tarifa actualizada: linea=%s tarifa=%s", linea.folio, tarifa)

        return Response(
            {
                "id": linea.id,
                "folio": linea.folio,
                "nombre_recorrido": linea.nombre_recorrido,
                "tarifa_actual": str(linea.tarifa_actual),
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# ETA - Calculo de tiempo estimado de llegada (CLIENTE)
# =============================================================================
class ETACalcularView(APIView):
    """
    Calcula el ETA (tiempo estimado de llegada) para un pasajero.

    Usa la ultima posicion de telemetria de los conductores en turno de la
    linea solicitada y calcula distancia Haversine hasta el pasajero.
    """

    permission_classes = [EsCliente]

    @extend_schema(
        tags=["Pasajero - ETA"],
        request=ETACalcularSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = ETACalcularSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        linea_id = serializer.validated_data["linea_id"]
        lat_pasajero = serializer.validated_data["latitud_pasajero"]
        lon_pasajero = serializer.validated_data["longitud_pasajero"]

        try:
            linea = LineaColectiva.objects.get(id=linea_id)
        except LineaColectiva.DoesNotExist:
            return Response(
                {
                    "error": "linea_no_encontrada",
                    "detail": "La linea especificada no existe.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Buscar conductores en turno de esta linea con vehiculo asignado
        conductores = (
            Conductor.objects.select_related("vehiculo")
            .filter(en_turno=True, vehiculo__linea_id=linea_id)
        )

        if not conductores.exists():
            return Response(
                {
                    "error": "sin_conductores_disponibles",
                    "detail": "No hay conductores en turno para esta linea.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Obtener ultima ubicacion de cada conductor desde MongoDB
        resultados = []
        coleccion = mongo.get_collection()
        for conductor in conductores:
            ultimo = (
                coleccion.find(
                    {
                        "id_vehiculo": conductor.vehiculo.id,
                    }
                )
                .sort("timestamp", -1)
                .limit(1)
            )
            doc = next(ultimo, None)
            if doc:
                coords = doc["ubicacion"]["coordinates"]
                lon, lat = coords[0], coords[1]
                distancia_km = haversine_km(lat_pasajero, lon_pasajero, lat, lon)
                # Asumir velocidad promedio 30 km/h en ciudad
                velocidad_promedio_kmh = 30.0
                eta_segundos = int((distancia_km / velocidad_promedio_kmh) * 3600)
                resultados.append(
                    {
                        "conductor_id": conductor.id,
                        "folio_conatacoch": conductor.folio_conatacoch,
                        "patente": conductor.vehiculo.patente,
                        "distancia_km": round(distancia_km, 2),
                        "eta_segundos": eta_segundos,
                        "eta_minutos": round(eta_segundos / 60, 1),
                        "cupos_disponibles": conductor.cupos_disponibles,
                        "ultima_actualizacion": doc["timestamp"].isoformat(),
                    }
                )

        # Ordenar por ETA mas cercano
        resultados.sort(key=lambda x: x["eta_segundos"])

        return Response(
            {
                "linea_id": linea_id,
                "nombre_recorrido": linea.nombre_recorrido,
                "pasajero": {"latitud": lat_pasajero, "longitud": lon_pasajero},
                "conductor_mas_cercano": resultados[0] if resultados else None,
                "opciones": resultados,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# TELEMETRIA - Envío de GPS con anti-spoofing (CONDUCTOR)
# =============================================================================
class TelemetriaEnviarView(APIView):
    """
    Recepcion de telemetria GPS del conductor con filtro cinematico
    anti-GPS-spoofing.

    Rechaza con HTTP 422 si la velocidad calculada supera 130 km/h respecto
    al ultimo punto registrado en MongoDB.
    """

    permission_classes = [EsConductor]

    @extend_schema(
        tags=["Conductor - Telemetria"],
        request=TelemetriaEnviarSerializer,
        responses={201: OpenApiTypes.OBJECT, 422: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        # Defensa explicita contra inyeccion NoSQL: ningun campo del payload
        # puede comenzar con '$' ni contener '.' (operadores MongoDB).
        claves_peligrosas = [
            clave
            for clave in request.data.keys()
            if isinstance(clave, str) and (clave.startswith("$") or "." in clave)
        ]
        if claves_peligrosas:
            logger.error(
                "Intento de inyeccion NoSQL en telemetria: campos=%s",
                claves_peligrosas,
            )
            return Response(
                {
                    "error": "payload_no_permitido",
                    "detail": "El payload contiene campos no permitidos.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TelemetriaEnviarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = request.user
        try:
            conductor = usuario.conductor
        except Conductor.DoesNotExist:
            return Response(
                {
                    "error": "sin_perfil_conductor",
                    "detail": "El usuario autenticado no tiene perfil de conductor.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not conductor.en_turno:
            return Response(
                {
                    "error": "turno_no_iniciado",
                    "detail": "El conductor debe iniciar turno antes de enviar telemetria.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        latitud = serializer.validated_data["latitud"]
        longitud = serializer.validated_data["longitud"]
        velocidad = serializer.validated_data["velocidad_kmh"]
        rumbo = serializer.validated_data["rumbo"]
        cupos = serializer.validated_data["cupos_disponibles"]
        timestamp = serializer.validated_data.get("timestamp") or timezone.now()

        # Garantiza 2dsphere + TTL en Atlas aunque el seed no haya corrido en
        # este proceso; la llamada es idempotente y no bloquea si Atlas falla.
        mongo.ensure_indexes_once()

        # --- Filtro cinematico anti-GPS-spoofing ---
        coleccion = mongo.get_collection()
        ultimo_punto = (
            coleccion.find(
                {
                    "id_vehiculo": conductor.vehiculo.id,
                }
            )
            .sort("timestamp", -1)
            .limit(1)
        )
        ultimo_doc = next(ultimo_punto, None)

        alerta_spoofing = False
        velocidad_calculada_kmh = velocidad

        if ultimo_doc:
            coords = ultimo_doc["ubicacion"]["coordinates"]
            lat_ant, lon_ant = coords[1], coords[0]
            ts_ant = ultimo_doc["timestamp"]
            velocidad_calculada_kmh = calcular_velocidad_kmh(
                lat_ant, lon_ant, ts_ant, latitud, longitud, timestamp
            )

        # Sin punto previo se valida la velocidad reportada; con punto previo
        # se valida la velocidad calculada por Haversine. Se rechaza (422)
        # cualquier valor que supere el umbral fisico de 130 km/h.
        if es_velocidad_sospechosa(velocidad_calculada_kmh) or es_velocidad_sospechosa(
            velocidad
        ):
            alerta_spoofing = True
            logger.warning(
                "ALERTA GPS Spoofing: vehiculo=%d velocidad_calc=%.2f kmh "
                "reportada=%.2f kmh punto_previo=%s",
                conductor.vehiculo.id,
                velocidad_calculada_kmh,
                velocidad,
                bool(ultimo_doc),
            )
            return Response(
                {
                    "error": "velocidad_sospechosa",
                    "detail": (
                        "La velocidad supera el maximo fisico permitido "
                        f"({VELOCIDAD_MAXIMA_KMH:.0f} km/h). Envio rechazado."
                    ),
                    "velocidad_reportada_kmh": velocidad,
                    "velocidad_calculada_kmh": round(velocidad_calculada_kmh, 2),
                    "alerta_spoofing": True,
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Sanitizar documento antes de insertar en MongoDB (anti-NoSQL injection)
        documento = validar_documento_mongo(
            {
                "id_vehiculo": conductor.vehiculo.id,
                "id_conductor": conductor.id,
                "folio_linea": conductor.folio_conatacoch,
                "cupos_disponibles": cupos,
                "latitud": latitud,
                "longitud": longitud,
                "velocidad_kmh": velocidad,
                "velocidad_calculada_kmh": round(velocidad_calculada_kmh, 2),
                "rumbo": rumbo,
                "alerta_spoofing": alerta_spoofing,
                "timestamp": timestamp,
            },
            campo_origen="telemetria_enviar",
        )

        insertar_ubicacion(
            id_vehiculo=documento["id_vehiculo"],
            id_conductor=documento["id_conductor"],
            folio_linea=documento["folio_linea"],
            cupos_disponibles=documento["cupos_disponibles"],
            latitud=documento["latitud"],
            longitud=documento["longitud"],
            velocidad_kmh=documento["velocidad_kmh"],
            rumbo=documento["rumbo"],
            timestamp=parse_datetime(documento["timestamp"])
            if isinstance(documento["timestamp"], str)
            else documento["timestamp"],
        )

        # Actualizar cupos del conductor en MySQL
        conductor.cupos_disponibles = cupos
        conductor.save(update_fields=["cupos_disponibles"])

        return Response(
            {
                "status": "ok",
                "id_vehiculo": conductor.vehiculo.id,
                "velocidad_reportada_kmh": velocidad,
                "velocidad_calculada_kmh": round(velocidad_calculada_kmh, 2),
                "alerta_spoofing": alerta_spoofing,
                "timestamp": documento["timestamp"],
            },
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# CONDUCTOR - Inicio de turno con 2FA y sesion unica
# =============================================================================
class ConductorIniciarTurnoView(APIView):
    """
    Inicio de turno de conductor con autenticacion de 2 factores (OTP).

    Flujo:
      1. Valida que el usuario sea CONDUCTOR y no tenga turno activo.
      2. Genera codigo OTP de 6 digitos y lo almacena con expiracion (5 min).
      3. Valida el codigo OTP enviado por el cliente.
      4. Invalida cualquier token_sesion_activa previa (sesion unica).
      5. Marca en_turno=True y genera nuevo token de sesion.
    """

    permission_classes = [PuedeIniciarTurno]

    @extend_schema(
        tags=["Conductor - Turno"],
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        usuario = request.user
        conductor = usuario.conductor

        codigo_entrado = request.data.get("codigo_otp")
        solicitar_codigo = request.data.get("solicitar_codigo", False)

        if solicitar_codigo or not codigo_entrado:
            # Generar y entregar codigo OTP (en realidad se enviaria por SMS)
            codigo = generar_codigo_otp()
            conductor.otp_codigo = codigo
            conductor.otp_codigo_expira = timezone.now() + timedelta(
                minutes=settings.OTP_EXPIRACION_MINUTOS
            )
            conductor.save(update_fields=["otp_codigo", "otp_codigo_expira"])
            logger.info(
                "OTP generado para conductor %s: %s (expires in %d min)",
                conductor.folio_conatacoch,
                codigo,
                settings.OTP_EXPIRACION_MINUTOS,
            )
            return Response(
                {
                    "estado": "otp_requerido",
                    "detail": "Se requiere codigo OTP para iniciar turno.",
                    "codigo_otp": codigo,  # En produccion enviar por SMS, no exponer
                    "expires_in_minutes": settings.OTP_EXPIRACION_MINUTOS,
                },
                status=status.HTTP_200_OK,
            )

        # Validar codigo OTP
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

        # OTP valido - iniciar turno con sesion unica
        # Invalidar sesion previa si existe
        if conductor.token_sesion_activa:
            logger.warning(
                "Invalidando sesion previa del conductor %s (sesion unica).",
                conductor.folio_conatacoch,
            )
        conductor.clear_token_sesion()
        conductor.en_turno = True
        conductor.otp_codigo = ""
        conductor.otp_codigo_expira = None

        # Generar nuevo token de sesion y almacenar solo su hash
        import secrets

        token_sesion = secrets.token_urlsafe(32)
        conductor.set_token_sesion(token_sesion)

        conductor.save(
            update_fields=[
                "en_turno",
                "otp_codigo",
                "otp_codigo_expira",
                "token_sesion_activa",
            ]
        )

        logger.info("Turno iniciado: conductor=%s folio=%s", usuario.email, conductor.folio_conatacoch)

        return Response(
            {
                "estado": "turno_iniciado",
                "conductor": conductor.folio_conatacoch,
                "patente": conductor.vehiculo.patente,
                "en_turno": True,
                "token_sesion": token_sesion,  # Solo se entrega una vez
            },
            status=status.HTTP_200_OK,
        )


class ConductorCuposView(APIView):
    """Cambio de cupos disponibles del conductor en turno."""

    permission_classes = [EsConductor]

    @extend_schema(
        tags=["Conductor - Cupos"],
        request=CambioCuposSerializer,
    )
    def post(self, request):
        usuario = request.user
        try:
            conductor = usuario.conductor
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
                    "error": "turno_no_iniciado",
                    "detail": "El conductor debe tener turno iniciado.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CambioCuposSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conductor.cupos_disponibles = serializer.validated_data["cupos_disponibles"]
        conductor.save(update_fields=["cupos_disponibles"])

        logger.info(
            "Cupos actualizados: conductor=%s cupos=%s",
            conductor.folio_conatacoch,
            conductor.cupos_disponibles,
        )

        return Response(
            {
                "conductor": conductor.folio_conatacoch,
                "cupos_disponibles": conductor.cupos_disponibles,
                "en_turno": conductor.en_turno,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# PAGOS QR - Flujo de pago digital (CLIENTE genera, CONDUCTOR confirma)
# =============================================================================
class PagoQRView(APIView):
    """
    Genera un codigo QR para pago digital (pasajero).

    Crea una TransaccionPago en estado PENDIENTE y retorna el codigo QR
    para que el conductor lo confirme.
    """

    permission_classes = [EsCliente]

    @extend_schema(
        tags=["Pagos - QR"],
        request=PagoQRSerializer,
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = PagoQRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = request.user
        conductor_id = serializer.validated_data["conductor_id"]
        linea_id = serializer.validated_data["linea_id"]
        monto = serializer.validated_data["monto"]

        try:
            conductor = Conductor.objects.select_related("vehiculo").get(id=conductor_id)
        except Conductor.DoesNotExist:
            return Response(
                {
                    "error": "conductor_no_encontrado",
                    "detail": "El conductor especificado no existe.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            linea = LineaColectiva.objects.get(id=linea_id)
        except LineaColectiva.DoesNotExist:
            return Response(
                {
                    "error": "linea_no_encontrada",
                    "detail": "La linea especificada no existe.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not conductor.en_turno:
            return Response(
                {
                    "error": "conductor_no_disponible",
                    "detail": "El conductor no esta en turno.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            transaccion = TransaccionPago.objects.create(
                pasajero=usuario,
                conductor=conductor,
                linea=linea,
                monto=monto,
                estado=TransaccionPago.Estado.PENDIENTE,
            )

            logger.info(
                "Pago QR generado: qr=%s pasajero=%s conductor=%s monto=%s",
                transaccion.codigo_qr_uuid,
                usuario.email,
                conductor.folio_conatacoch,
                monto,
            )

        return Response(
            {
                "codigo_qr_uuid": str(transaccion.codigo_qr_uuid),
                "estado": transaccion.estado,
                "monto": str(transaccion.monto),
                "conductor_folio": conductor.folio_conatacoch,
                "linea_folio": linea.folio,
                "fecha_hora": transaccion.fecha_hora.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class PagoConfirmarView(APIView):
    """
    Confirma un pago QR (conductor).

    Valida que el QR exista, este PENDIENTE, pertenezca al conductor
    autenticado y lo marca como PAGADO.
    """

    permission_classes = [EsConductor]

    @extend_schema(
        tags=["Pagos - QR"],
        request=PagoConfirmarSerializer,
    )
    def post(self, request):
        serializer = PagoConfirmarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = request.user
        try:
            conductor = usuario.conductor
        except Conductor.DoesNotExist:
            return Response(
                {
                    "error": "sin_perfil_conductor",
                    "detail": "El usuario no tiene perfil de conductor.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        codigo_qr = serializer.validated_data["codigo_qr_uuid"]

        try:
            transaccion = TransaccionPago.objects.select_related(
                "pasajero", "conductor", "linea"
            ).get(codigo_qr_uuid=codigo_qr)
        except TransaccionPago.DoesNotExist:
            return Response(
                {
                    "error": "qr_no_encontrado",
                    "detail": "El codigo QR no corresponde a una transaccion valida.",
                    "status_code": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Propiedad de recurso: el QR debe pertenecer al conductor autenticado
        if transaccion.conductor_id != conductor.id:
            logger.warning(
                "IDOR detectado: conductor %s intenta confirmar QR de conductor %s",
                conductor.folio_conatacoch,
                transaccion.conductor.folio_conatacoch,
            )
            return Response(
                {
                    "error": "acceso_denegado",
                    "detail": "No es el conductor asignado a este pago.",
                    "status_code": status.HTTP_403_FORBIDDEN,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if transaccion.estado != TransaccionPago.Estado.PENDIENTE:
            return Response(
                {
                    "error": "transaccion_no_pendiente",
                    "detail": f"El pago ya esta en estado {transaccion.estado}.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            transaccion.estado = TransaccionPago.Estado.PAGADO
            transaccion.save(update_fields=["estado"])

            logger.info(
                "Pago confirmado: qr=%s conductor=%s monto=%s",
                codigo_qr,
                conductor.folio_conatacoch,
                transaccion.monto,
            )

        return Response(
            {
                "codigo_qr_uuid": str(transaccion.codigo_qr_uuid),
                "estado": transaccion.estado,
                "monto": str(transaccion.monto),
                "pasajero_rut": transaccion.pasajero.rut,
                "linea_folio": transaccion.linea.folio,
                "fecha_hora": transaccion.fecha_hora.isoformat(),
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# ViewSets existentes con permisos actualizados (RBAC)
# =============================================================================

# VehiculoViewSet ya existe en views.py; se deja intacto.
# ConductorViewSet ya existe con IsAuthenticated; se actualiza para RBAC.


@extend_schema_view(
    list=extend_schema(tags=["Conductores"]),
    retrieve=extend_schema(tags=["Conductores"]),
)
class ConductorViewSetRBAC(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de conductores con permisos RBAC estrictos.
    - ADMIN: puede ver todos.
    - CONDUCTOR: solo puede ver su propio perfil.
    - CLIENTE: no tiene acceso (403).
    """

    serializer_class = ConductorSerializer
    permission_classes = [IsAuthenticated, EsAdminOPropietarioRecurso]
    search_fields = ["folio_conatacoch", "usuario__rut", "vehiculo__patente"]
    ordering = ["folio_conatacoch"]

    def get_queryset(self):
        usuario = self.request.user
        base = Conductor.objects.select_related(
            "usuario", "vehiculo", "vehiculo__linea"
        ).order_by("folio_conatacoch")
        if usuario.rol == Usuario.Rol.ADMIN:
            return base
        # En listados el conductor solo ve su perfil; en retrieve se devuelve
        # el objeto completo para que el permiso de objeto responda 403 (IDOR).
        if getattr(self, "action", None) == "list":
            return base.filter(usuario_id=usuario.id)
        return base

    def get_propietario_id(self, obj):
        return obj.usuario_id
