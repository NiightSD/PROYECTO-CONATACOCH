"""Rutas raiz del proyecto CONATACOCH."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from core.views_fase3 import TokenObtainPairConRolView

admin.site.site_header = "CONATACOCH - Administracion"
admin.site.site_title = "CONATACOCH"
admin.site.index_title = "Panel de administracion"

urlpatterns = [
    path("admin/", admin.site.urls),

    # Documentacion OpenAPI (requerida en /api/docs/).
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Autenticacion JWT (incluye el rol exacto en la respuesta).
    path(
        "api/token/",
        TokenObtainPairConRolView.as_view(),
        name="token_obtain_pair",
    ),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # API de negocio.
    path("api/", include("core.urls")),
]

# -----------------------------------------------------------------------------
# Panel web en desarrollo (mismo origen => API="/api" funciona sin proxy Nginx).
# En produccion Nginx sirve web-admin/ y hace reverse proxy de /api.
# -----------------------------------------------------------------------------
if settings.DEBUG:
    _web_admin_dir = settings.BASE_DIR.parent / "web-admin"
    urlpatterns += [
        path(
            "panel/",
            serve,
            {"path": "index.html", "document_root": _web_admin_dir},
            name="web-admin-panel",
        ),
        re_path(
            r"^panel/(?P<path>.*)$",
            serve,
            {"document_root": _web_admin_dir},
            name="web-admin-assets",
        ),
    ]
