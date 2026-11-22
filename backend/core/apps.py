from django.apps import AppConfig
from django.db.backends.signals import connection_created


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Nucleo CONATACOCH"

    def ready(self) -> None:
        # No se abre conexion a Mongo en el arranque: la app debe poder iniciar
        # aunque Atlas no este disponible (los indices se crean por comando).
        connection_created.connect(_configurar_sqlite)


def _configurar_sqlite(sender, connection, **kwargs) -> None:
    """Activa WAL y un busy timeout amplio para cargas concurrentes en SQLite."""
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
