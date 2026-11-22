"""Registro de modelos en el admin de Django."""
from django.contrib import admin

from core.models import (
    Conductor,
    LineaColectiva,
    Paradero,
    TransaccionPago,
    Usuario,
    Vehiculo,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("rut", "nombre", "email", "rol", "activo", "intentos_fallidos", "is_staff")
    list_filter = ("rol", "activo", "is_staff")
    search_fields = ("rut", "nombre", "email")
    ordering = ("nombre",)
    # El hash nunca se muestra ni se edita desde el admin.
    exclude = ("password", "groups", "user_permissions")


@admin.register(LineaColectiva)
class LineaColectivaAdmin(admin.ModelAdmin):
    list_display = (
        "folio",
        "nombre_recorrido",
        "tipo_trazado",
        "comuna_origen",
        "comuna_destino",
        "tarifa_actual",
    )
    list_filter = ("region", "tipo_servicio", "tipo_trazado", "comuna_origen")
    search_fields = ("folio", "nombre_recorrido", "comuna_origen", "comuna_destino")
    ordering = ("folio", "nombre_recorrido")


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("patente", "marca_modelo", "capacidad_pasajeros", "linea")
    list_filter = ("linea__region",)
    search_fields = ("patente", "marca_modelo")
    autocomplete_fields = ("linea",)


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = (
        "folio_conatacoch",
        "usuario",
        "vehiculo",
        "en_turno",
        "cupos_disponibles",
    )
    list_filter = ("en_turno", "vehiculo__linea")
    search_fields = ("folio_conatacoch", "usuario__rut", "usuario__nombre", "vehiculo__patente")
    autocomplete_fields = ("usuario", "vehiculo")
    exclude = ("otp_secreto", "token_sesion_activa")


@admin.register(Paradero)
class ParaderoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "comuna", "latitud", "longitud", "linea")
    list_filter = ("comuna",)
    search_fields = ("nombre", "comuna", "linea__folio")
    autocomplete_fields = ("linea",)


@admin.register(TransaccionPago)
class TransaccionPagoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_qr_uuid",
        "pasajero",
        "conductor",
        "linea",
        "monto",
        "estado",
        "fecha_hora",
    )
    list_filter = ("estado", "fecha_hora", "linea__region")
    search_fields = ("codigo_qr_uuid", "pasajero__rut", "conductor__folio_conatacoch")
    readonly_fields = ("codigo_qr_uuid", "fecha_hora")
    date_hierarchy = "fecha_hora"
