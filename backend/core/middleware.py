"""
Middleware aditivo de desarrollo.

El panel web (`web-admin/`) se puede servir de dos formas:

  * Con Nginx/Docker en http://localhost:8080 (mismo origen via proxy `/api`).
  * Abierto con un servidor estatico distinto al backend (por ejemplo
    http://127.0.0.1:8080) mientras Django corre en http://127.0.0.1:8000.

En el segundo caso el navegador exige cabeceras CORS. Este middleware las
agrega **solo con DEBUG=True** y solo a rutas `/api/`, sin afectar produccion
ni las pruebas. No requiere la dependencia django-cors-headers.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


class DevCorsMiddleware:
    """CORS permisivo y acotado para origenes locales de desarrollo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        es_api = request.path.startswith("/api/")
        es_preflight = request.method == "OPTIONS" and es_api

        if settings.DEBUG and es_preflight:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if not (settings.DEBUG and es_api):
            return response

        origen = request.headers.get("Origin", "")
        permitidos = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        if origen and origen in permitidos:
            response["Access-Control-Allow-Origin"] = origen
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, Accept, X-Requested-With"
            )
            response["Access-Control-Allow-Methods"] = (
                "GET, POST, PATCH, DELETE, OPTIONS"
            )
            response["Access-Control-Max-Age"] = "600"
        return response
