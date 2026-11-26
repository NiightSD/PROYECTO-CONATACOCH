"""Crea (idempotente) los indices de MongoDB y reporta el estado de Atlas."""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core import mongo


class Command(BaseCommand):
    help = "Crea indices 2dsphere, compuesto y TTL en MongoDB (Atlas o local)."

    def handle(self, *args, **options):
        modo = "Atlas" if settings.MONGO_ATLAS_URI else "local"
        self.stdout.write(
            f"[mongo] destino={modo} db={settings.MONGO_DB_NAME} "
            f"coleccion={settings.MONGO_COLLECTION} ttl={settings.MONGO_TTL_SECONDS}s"
        )
        try:
            nombres = mongo.ensure_indexes()
        except Exception as exc:
            mongo.reset_client()
            raise CommandError(f"No se pudieron crear los indices: {exc}") from exc

        for clave, nombre in nombres.items():
            self.stdout.write(f"  [ok] {clave:<18} {nombre}")
        self.stdout.write(self.style.SUCCESS("[mongo] indices listos."))
