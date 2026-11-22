"""Rutas de la API de negocio - CONATACOCH Fase 1 + Fase 2."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import (
    ConductorViewSet,
    HealthLiveView,
    HealthView,
    LineaColectivaViewSet,
    ParaderoViewSet,
    StatsView,
    TransaccionPagoViewSet,
    VehiculoViewSet,
)
from core.views_fase2 import (
    AdminConductorCreateView,
    AdminConductorListView,
    AdminLineaView,
    AdminTarifaView,
    AuthLoginView,
    AuthRefreshView,
    ConductorCuposView,
    ConductorIniciarTurnoView,
    ConductorViewSetRBAC,
    ETACalcularView,
    PagoConfirmarView,
    PagoQRView,
    TelemetriaEnviarView,
)

router = DefaultRouter()
router.register("lineas", LineaColectivaViewSet, basename="linea")
router.register("paraderos", ParaderoViewSet, basename="paradero")
router.register("vehiculos", VehiculoViewSet, basename="vehiculo")
router.register("conductores", ConductorViewSet, basename="conductor")
router.register("transacciones", TransaccionPagoViewSet, basename="transaccion")

# ViewSet RBAC para conductores (endpoints alternativos con permisos estrictos)
router.register("conductores-rbac", ConductorViewSetRBAC, basename="conductor-rbac")

urlpatterns = [
    path("health/live/", HealthLiveView.as_view(), name="health-live"),
    path("health/", HealthView.as_view(), name="health"),
    path("stats/", StatsView.as_view(), name="stats"),
    path("", include(router.urls)),
]

# ---------------------------------------------------------------------------
# Endpoints de Fase 2 - Autenticacion y seguridad
# ---------------------------------------------------------------------------
urlpatterns += [
    path("auth/login/", AuthLoginView.as_view(), name="auth-login"),
    path("auth/refresh/", AuthRefreshView.as_view(), name="auth-refresh"),
]

# ---------------------------------------------------------------------------
# Endpoints de Fase 2 - Admin (solo ADMIN)
# ---------------------------------------------------------------------------
urlpatterns += [
    path("admin-api/conductores/", AdminConductorListView.as_view(), name="admin-conductores-list"),
    path("admin-api/conductores/registro/", AdminConductorCreateView.as_view(), name="admin-conductor-registro"),
    path("admin-api/lineas/", AdminLineaView.as_view(), name="admin-linea"),
    path("admin-api/tarifas/", AdminTarifaView.as_view(), name="admin-tarifa"),
]

# ---------------------------------------------------------------------------
# Endpoints de Fase 2 - Pasajero / Cliente
# ---------------------------------------------------------------------------
urlpatterns += [
    path("eta/calcular/", ETACalcularView.as_view(), name="eta-calcular"),
    path("pagos/qr/", PagoQRView.as_view(), name="pago-qr"),
]

# ---------------------------------------------------------------------------
# Endpoints de Fase 2 - Conductor
# ---------------------------------------------------------------------------
urlpatterns += [
    path("telemetria/enviar/", TelemetriaEnviarView.as_view(), name="telemetria-enviar"),
    path("conductor/iniciar-turno/", ConductorIniciarTurnoView.as_view(), name="conductor-iniciar-turno"),
    path("conductor/cupos/", ConductorCuposView.as_view(), name="conductor-cupos"),
    path("pagos/confirmar/", PagoConfirmarView.as_view(), name="pago-confirmar"),
]
