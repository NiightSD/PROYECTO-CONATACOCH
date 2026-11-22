"""Espera activa a que MySQL acepte conexiones (defensa extra al healthcheck)."""
from __future__ import annotations

import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Bloquea el arranque hasta que la base de datos relacional responda."

    def add_arguments(self, parser):
        parser.add_argument(
            "--retries",
            type=int,
            default=getattr(settings, "DB_WAIT_RETRIES", 30),
            help="Numero de intentos (default: 30).",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=2.0,
            help="Segundos entre intentos (default: 2).",
        )

    def handle(self, *args, **options):
        retries = int(options["retries"])
        delay = float(options["delay"])
        last_error: Exception | None = None

        for intento in range(1, retries + 1):
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[wait_for_db] MySQL disponible (intento {intento}/{retries})."
                    )
                )
                return
            except OperationalError as exc:
                last_error = exc
                self.stderr.write(
                    f"[wait_for_db] MySQL no disponible ({intento}/{retries}): {exc}"
                )
                time.sleep(delay)

        raise CommandError(f"MySQL no respondio tras {retries} intentos: {last_error}")
