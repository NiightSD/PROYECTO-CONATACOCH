"""
Acceso a MongoDB (Atlas prioritario / fallback local) con PyMongo.

Base documental: telemetria_ubicacion
Coleccion: ubicaciones

Documento GeoJSON (Fase 2 lo alimenta en tiempo real):
{
  "_id": ObjectId,
  "id_vehiculo": 12,
  "id_conductor": 4,
  "folio_linea": "234001",
  "cupos_disponibles": 3,
  "ubicacion": {"type": "Point", "coordinates": [longitud, latitud]},
  "velocidad_kmh": 38.5,
  "rumbo": 270,
  "timestamp": ISODate("2026-11-21T14:30:00Z")
}

Indices creados automaticamente:
  1. 2dsphere sobre "ubicacion"          -> consultas geoespaciales $near / $geoWithin.
  2. Compuesto (folio_linea, timestamp)  -> ultima posicion por recorrido.
  3. TTL sobre "timestamp" (14400 s)     -> retencion de 4 horas.
"""
from __future__ import annotations

import atexit
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from django.conf import settings

logger = logging.getLogger("core.mongo")

_client = None
_client_lock = threading.Lock()


def get_client():
    """Cliente PyMongo singleton por proceso, con pool de conexiones."""
    global _client
    if _client is not None:
        return _client

    with _client_lock:
        if _client is not None:
            return _client

        if getattr(settings, "MONGO_MOCK", False):
            import mongomock

            logger.warning(
                "MONGO_MOCK activo: usando mongomock en memoria (solo pruebas)."
            )
            _client = mongomock.MongoClient()
            return _client

        from pymongo import MongoClient

        kwargs: dict[str, Any] = {
            "maxPoolSize": settings.MONGO_MAX_POOL_SIZE,
            "minPoolSize": settings.MONGO_MIN_POOL_SIZE,
            "serverSelectionTimeoutMS": settings.MONGO_TIMEOUT_MS,
            "connectTimeoutMS": settings.MONGO_TIMEOUT_MS,
            "socketTimeoutMS": settings.MONGO_TIMEOUT_MS * 2,
            "retryWrites": True,
            "appname": "conatacoch-backend",
        }
        # Atlas exige TLS; el fallback local no lo usa.
        if settings.MONGO_USE_TLS:
            kwargs["tls"] = True

        logger.info(
            "Conectando a MongoDB (%s) db=%s pool=%s",
            "Atlas/TLS" if settings.MONGO_ATLAS_URI else "local",
            settings.MONGO_DB_NAME,
            settings.MONGO_MAX_POOL_SIZE,
        )
        _client = MongoClient(settings.MONGO_URI, **kwargs)

    return _client


def reset_client() -> None:
    """Cierra y descarta el cliente singleton.

    Se usa cuando Atlas rechaza las credenciales: sin esto PyMongo mantiene un
    monitor en segundo plano reintentando y llenando el log de errores. La
    proxima llamada a `get_client()` vuelve a intentar la conexion.
    """
    global _client
    with _client_lock:
        cliente, _client = _client, None
    if cliente is not None:
        try:
            cliente.close()
        except Exception:  # pragma: no cover - cierre defensivo
            pass


def get_database():
    return get_client()[settings.MONGO_DB_NAME]


def get_collection():
    return get_database()[settings.MONGO_COLLECTION]


def ensure_indexes() -> dict[str, str]:
    """Crea (idempotente) los indices requeridos y retorna sus nombres."""
    coleccion = get_collection()

    from pymongo import ASCENDING, DESCENDING, GEOSPHERE

    nombres = {}
    nombres["geo"] = coleccion.create_index(
        [("ubicacion", GEOSPHERE)], name="idx_ubicacion_2dsphere"
    )
    nombres["folio_timestamp"] = coleccion.create_index(
        [("folio_linea", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_folio_timestamp",
    )
    nombres["ttl"] = coleccion.create_index(
        [("timestamp", ASCENDING)],
        name="idx_timestamp_ttl",
        expireAfterSeconds=settings.MONGO_TTL_SECONDS,
    )
    # Indice de apoyo para la ultima posicion de un vehiculo.
    nombres["vehiculo_timestamp"] = coleccion.create_index(
        [("id_vehiculo", ASCENDING), ("timestamp", DESCENDING)],
        name="idx_vehiculo_timestamp",
    )
    return nombres


def ping(timeout_ms: int = 2000) -> tuple[bool, float]:
    """Ping liviano. Retorna (ok, latencia_ms)."""
    inicio = time.perf_counter()
    try:
        get_client().admin.command("ping")
        return True, round((time.perf_counter() - inicio) * 1000, 2)
    except Exception as exc:  # pragma: no cover - depende de red externa
        logger.warning("Ping MongoDB fallo: %s", exc)
        return False, round((time.perf_counter() - inicio) * 1000, 2)


def insertar_ubicacion(
    *,
    id_vehiculo: int,
    id_conductor: int,
    folio_linea: str,
    cupos_disponibles: int,
    latitud: float,
    longitud: float,
    velocidad_kmh: float = 0.0,
    rumbo: float = 0.0,
    timestamp: datetime | None = None,
):
    """
    Inserta un documento de telemetria GeoJSON.

    GeoJSON usa orden [longitud, latitud]. El timestamp debe ser UTC para que
    el indice TTL elimine el documento a las 4 horas.
    """
    from pymongo import ReturnDocument  # noqa: F401  (disponible para Fase 2)

    if not (-90 <= latitud <= 90 and -180 <= longitud <= 180):
        raise ValueError("Coordenadas fuera de rango.")

    documento = {
        "id_vehiculo": int(id_vehiculo),
        "id_conductor": int(id_conductor),
        "folio_linea": str(folio_linea),
        "cupos_disponibles": int(cupos_disponibles),
        "ubicacion": {
            "type": "Point",
            "coordinates": [float(longitud), float(latitud)],
        },
        "velocidad_kmh": float(velocidad_kmh),
        "rumbo": float(rumbo),
        "timestamp": timestamp or datetime.now(timezone.utc),
    }
    return get_collection().insert_one(documento)


@atexit.register
def close_client() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        finally:
            _client = None
