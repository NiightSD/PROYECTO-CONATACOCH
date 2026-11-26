import logging
import os
import sys

from django.apps import AppConfig
from django.db.backends.signals import connection_created

logger = logging.getLogger("core.apps")


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Nucleo CONATACOCH"

    def ready(self) -> None:
        connection_created.connect(_configurar_sqlite)
        _asegurar_indices_mongo()


def _asegurar_indices_mongo() -> None:
    """Crea los indices 2dsphere/TTL al arrancar (Atlas o fallback local).

    Nunca aborta el arranque: si Atlas no responde, el backend sigue operativo
    en modo degradado y el comando `manage.py mongo_indexes` permite reintentar.
    """
    if os.getenv("MONGO_ENSURE_INDEXES", "true").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return
    if "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ:
        return
    if os.getenv("MONGO_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}:
        return

    try:
        from core import mongo

        nombres = mongo.ensure_indexes()
        logger.info("Indices MongoDB asegurados: %s", nombres)
    except Exception as exc:  # pragma: no cover - depende de red/credenciales
        logger.warning("No se pudieron crear los indices MongoDB: %s", exc)
        try:
            from core import mongo

            mongo.reset_client()
        except Exception:  # pragma: no cover - cierre defensivo
            pass


def _configurar_sqlite(sender, connection, **kwargs) -> None:
    """Activa WAL y un busy timeout amplio para cargas concurrentes en SQLite."""
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
