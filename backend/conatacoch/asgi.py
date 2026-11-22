"""Punto de entrada ASGI (preparado para streaming de telemetria en Fase 2)."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conatacoch.settings")

application = get_asgi_application()
