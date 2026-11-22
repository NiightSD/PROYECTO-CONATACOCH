"""Crea los indices de MongoDB: 2dsphere, compuesto y TTL."""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core import mongo


class Command(BaseCommand):
    help = (
        "Crea indices idempotentes en MongoDB: 2dsphere (ubicacion), "
        "compuesto (folio_linea, timestamp) y TTL (timestamp)."
    )

    def handle(self, *args, **options):
        destino = "Atlas" if settings.MONGO_ATLAS_URI else "local"
        self.stdout.write(
            f"[mongo] Destino={destino} db={settings.MONGO_DB_NAME} "
            f"coleccion={settings.MONGO_COLLECTION} ttl={settings.MONGO_TTL_SECONDS}s"
        )
        try:
            nombres = mongo.ensure_indexes()
        except Exception as exc:
            raise CommandError(f"No se pudieron crear los indices MongoDB: {exc}") from exc

        for clave, nombre in nombres.items():
            self.stdout.write(self.style.SUCCESS(f"[mongo] Indice listo: {nombre} ({clave})"))
