"""
Permisos DRF basados en roles (RBAC) y propiedad de recurso para CONATACOCH.

Roles soportados: ADMIN, CONDUCTOR, CLIENTE.
Controla acceso a endpoints y previene IDOR (Insecure Direct Object Reference).
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.models import Usuario


class EsAdmin(BasePermission):
    """Solo usuarios con rol ADMIN."""

    message = "Solo un administrador puede realizar esta accion."

    def has_permission(self, request, view) -> bool:
        usuario = getattr(request, "user", None)
        return bool(usuario and usuario.is_authenticated and usuario.rol == Usuario.Rol.ADMIN)


class EsConductor(BasePermission):
    """Solo usuarios con rol CONDUCTOR."""

    message = "Solo un conductor puede realizar esta accion."

    def has_permission(self, request, view) -> bool:
        usuario = getattr(request, "user", None)
        return bool(
            usuario
            and usuario.is_authenticated
            and usuario.rol == Usuario.Rol.CONDUCTOR
        )


class EsCliente(BasePermission):
    """Solo usuarios con rol CLIENTE (pasajero)."""

    message = "Solo un cliente/pasajero puede realizar esta accion."

    def has_permission(self, request, view) -> bool:
        usuario = getattr(request, "user", None)
        return bool(
            usuario and usuario.is_authenticated and usuario.rol == Usuario.Rol.CLIENTE
        )


class EsAdminOPropietarioRecurso(BasePermission):
    """
    Permite acceso si el usuario es ADMIN o es el propietario del recurso.

    Para prevenir IDOR, la vista debe implementar `get_propietario_id(obj)` o
    el objeto debe tener campo `usuario` o `pasajero` o `conductor.usuario`.
    """

    message = "No tiene permiso para acceder a este recurso (403)."

    def has_object_permission(self, request, view, obj) -> bool:
        usuario = getattr(request, "user", None)
        if not usuario or not usuario.is_authenticated:
            return False

        if usuario.rol == Usuario.Rol.ADMIN:
            return True

        # Campo directo usuario
        if hasattr(obj, "usuario") and obj.usuario_id == usuario.id:
            return True
        if hasattr(obj, "pasajero_id") and obj.pasajero_id == usuario.id:
            return True
        if hasattr(obj, "conductor_id") and hasattr(obj, "conductor"):
            try:
                if obj.conductor.usuario_id == usuario.id:
                    return True
            except AttributeError:
                pass

        # Metodo personalizado en la vista
        obtener = getattr(view, "get_propietario_id", None)
        if callable(obtener):
            try:
                return obtener(obj) == usuario.id
            except Exception:
                return False

        return False


class PuedeIniciarTurno(BasePermission):
    """
    Solo CONDUCTOR autenticado con perfil de conductor.

    Se permite reiniciar turno para que la vista pueda invalidar una sesion
    previa (sesion unica). Si el conductor ya esta en turno, el nuevo OTP
    reemplaza la sesion anterior.
    """

    message = "Solo un conductor con perfil habilitado puede iniciar turno."

    def has_permission(self, request, view) -> bool:
        usuario = getattr(request, "user", None)
        if not usuario or not usuario.is_authenticated:
            return False
        if usuario.rol != Usuario.Rol.CONDUCTOR:
            return False
        try:
            usuario.conductor
            return True
        except Usuario.conductor.RelatedObjectDoesNotExist:
            return False
