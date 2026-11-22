"""
Modelo de datos relacional de CONATACOCH (MySQL 8, 3FN).

Convenciones:
  * Nombres de tabla en singular y snake_case.
  * Claves primarias surrogate BIGINT autoincrementales.
  * Llaves foraneas con on_delete=PROTECT, que Django traduce a la semantica
    ON DELETE RESTRICT a nivel de ORM. MySQL/InnoDB ademas aplica RESTRICT por
    defecto a las FK, por lo que no se permite borrar filas referenciadas.
  * Indices B-Tree explicitos para las consultas de negocio (rut, patente,
    folio, comuna, fecha_hora, QR) y compuestos para filtros frecuentes.
  * Sin dependencias transitivas: cada atributo depende solo de la PK de su
    entidad; las relaciones se resuelven con FK (3FN).
"""
from __future__ import annotations

import hashlib
import re
import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from core.crypto import cifrar_secreto, descifrar_secreto


# -----------------------------------------------------------------------------
# Validadores de dominio chileno
# -----------------------------------------------------------------------------
def validar_rut(value: str) -> None:
    """Valida el digito verificador del RUT chileno (modulo 11)."""
    if not value:
        raise ValidationError("El RUT es obligatorio.")
    limpio = re.sub(r"[.\-\s]", "", str(value)).upper()
    if not re.fullmatch(r"\d{7,8}[0-9K]", limpio):
        raise ValidationError("Formato de RUT invalido. Ejemplo: 11.111.111-1")
    cuerpo, dv = limpio[:-1], limpio[-1]
    suma = sum(int(digito) * (2 + indice % 6) for indice, digito in enumerate(reversed(cuerpo)))
    resto = 11 - (suma % 11)
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    if dv != esperado:
        raise ValidationError("Digito verificador de RUT invalido.")


validador_patente = RegexValidator(
    regex=r"^[A-Z]{2,4}-?[0-9]{2,4}$",
    message="Patente invalida. Formatos aceptados: ABCD-12, AB-1234, BBBB12.",
)


# -----------------------------------------------------------------------------
# Usuario (tabla unica para ADMIN, CONDUCTOR y CLIENTE)
# -----------------------------------------------------------------------------
class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, rut: str, nombre: str, password: str | None = None, **extra):
        if not email:
            raise ValueError("El email es obligatorio.")
        if not rut:
            raise ValueError("El RUT es obligatorio.")
        email = self.normalize_email(email)
        usuario = self.model(email=email, rut=rut, nombre=nombre, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email: str, rut: str, nombre: str, password: str | None = None, **extra):
        extra.setdefault("rol", Usuario.Rol.ADMIN)
        extra.setdefault("activo", True)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True.")
        return self.create_user(email, rut, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Cuenta unica con rol discriminado (3FN: sin tablas de roles duplicadas)."""

    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        CONDUCTOR = "CONDUCTOR", "Conductor"
        CLIENTE = "CLIENTE", "Pasajero / Cliente"

    rut = models.CharField(
        "RUT",
        max_length=12,
        unique=True,  # Indice B-Tree unico
        validators=[validar_rut],
        help_text="RUT con formato 11.111.111-1",
    )
    nombre = models.CharField("nombre completo", max_length=150)
    email = models.EmailField(
        "correo electronico",
        unique=True,  # Indice B-Tree unico (usado como USERNAME_FIELD)
    )
    # Se conserva el nombre de columna exigido por el diseno: password_hash.
    password = models.CharField("password hash", max_length=128, db_column="password_hash")
    rol = models.CharField(
        "rol", max_length=10, choices=Rol.choices, default=Rol.CLIENTE, db_index=True
    )
    activo = models.BooleanField("activo", default=True)
    intentos_fallidos = models.PositiveSmallIntegerField("intentos fallidos", default=0)
    bloqueado_hasta = models.DateTimeField("bloqueado hasta", null=True, blank=True)
    is_staff = models.BooleanField("acceso admin", default=False)
    date_joined = models.DateTimeField("fecha de registro", default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["rut", "nombre"]
    EMAIL_FIELD = "email"

    class Meta:
        db_table = "usuario"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        indexes = [
            models.Index(fields=["rol", "activo"], name="idx_usuario_rol_activo"),
            models.Index(fields=["bloqueado_hasta"], name="idx_usuario_bloqueado"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.rut})"

    @property
    def is_active(self) -> bool:  # requerido por django.contrib.auth
        return self.activo

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.activo = value

    @property
    def password_hash(self) -> str:
        """Alias de solo lectura para mantener el vocabulario del diseno."""
        return self.password

    @property
    def esta_bloqueado(self) -> bool:
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > timezone.now())

    def registrar_login_exitoso(self) -> None:
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        self.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])

    def registrar_login_fallido(self, max_intentos: int = 5, minutos_bloqueo: int = 15) -> None:
        from datetime import timedelta

        self.intentos_fallidos += 1
        campos = ["intentos_fallidos"]
        if self.intentos_fallidos >= max_intentos:
            self.bloqueado_hasta = timezone.now() + timedelta(minutes=minutos_bloqueo)
            campos.append("bloqueado_hasta")
        self.save(update_fields=campos)


# -----------------------------------------------------------------------------
# LineaColectiva
# -----------------------------------------------------------------------------
class LineaColectiva(models.Model):
    """
    Recorrido autorizado del gremio.

    El dataset oficial (660 itinerarios) repite FOLIO en varios recorridos y
    algunos pares (folio, nombre_recorrido) se diferencian solo por el tipo de
    trazado (PRINCIPAL / ALTERNATIVO). La clave natural real es
    (folio, nombre_recorrido, tipo_trazado). Se mantiene un indice B-Tree sobre
    folio y una restriccion unica compuesta para preservar la integridad sin
    introducir redundancia (3FN).
    """

    class TipoServicio(models.TextChoices):
        URBANO = "AUTOMOVIL URBANO TAXI COLECTIVO", "Automovil urbano taxi colectivo"
        RURAL = "AUTOMOVIL RURAL TAXI COLECTIVO", "Automovil rural taxi colectivo"

    class TipoTrazado(models.TextChoices):
        PRINCIPAL = "PRINCIPAL", "Principal"
        ALTERNATIVO = "ALTERNATIVO", "Alternativo"

    region = models.PositiveSmallIntegerField("region", db_index=True)
    folio = models.PositiveIntegerField("folio", db_index=True)  # Indice B-Tree
    tipo_servicio = models.CharField("tipo de servicio", max_length=80, db_index=True)
    nombre_recorrido = models.CharField("nombre recorrido", max_length=50)
    tipo_trazado = models.CharField(
        "tipo de trazado", max_length=20, choices=TipoTrazado.choices, default=TipoTrazado.PRINCIPAL
    )
    nombre_origen = models.CharField("nombre origen", max_length=150)
    comuna_origen = models.CharField("comuna origen", max_length=100, db_index=True)
    domicilio_origen = models.CharField("domicilio origen", max_length=200)
    nombre_destino = models.CharField("nombre destino", max_length=150)
    comuna_destino = models.CharField("comuna destino", max_length=100, db_index=True)
    domicilio_destino = models.CharField("domicilio destino", max_length=200)
    tarifa_actual = models.DecimalField(
        "tarifa actual (CLP)",
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = "linea_colectiva"
        verbose_name = "linea colectiva"
        verbose_name_plural = "lineas colectivas"
        ordering = ["region", "folio", "nombre_recorrido"]
        constraints = [
            models.UniqueConstraint(
                fields=["folio", "nombre_recorrido", "tipo_trazado"],
                name="uq_linea_folio_recorrido_traza",
            ),
            models.CheckConstraint(
                condition=models.Q(region__gte=1) & models.Q(folio__gte=1),
                name="chk_linea_region_folio",
            ),
        ]
        indexes = [
            models.Index(fields=["region", "folio"], name="idx_linea_region_folio"),
            models.Index(fields=["comuna_origen"], name="idx_linea_comuna_origen"),
            models.Index(fields=["comuna_destino"], name="idx_linea_comuna_destino"),
        ]

    def __str__(self) -> str:
        return f"{self.folio} - {self.nombre_recorrido} ({self.comuna_origen} -> {self.comuna_destino})"


# -----------------------------------------------------------------------------
# Vehiculo
# -----------------------------------------------------------------------------
class Vehiculo(models.Model):
    patente = models.CharField(
        "patente",
        max_length=10,
        unique=True,  # Indice B-Tree unico
        validators=[validador_patente],
    )
    marca_modelo = models.CharField("marca y modelo", max_length=120)
    capacidad_pasajeros = models.PositiveSmallIntegerField(
        "capacidad de pasajeros",
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
    )
    linea = models.ForeignKey(
        LineaColectiva,
        verbose_name="linea asignada",
        on_delete=models.PROTECT,
        related_name="vehiculos",
    )

    class Meta:
        db_table = "vehiculo"
        verbose_name = "vehiculo"
        verbose_name_plural = "vehiculos"
        ordering = ["patente"]
        indexes = [
            models.Index(fields=["linea"], name="idx_vehiculo_linea"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacidad_pasajeros__gte=1)
                & models.Q(capacidad_pasajeros__lte=30),
                name="chk_vehiculo_capacidad",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.patente} ({self.marca_modelo})"


# -----------------------------------------------------------------------------
# Conductor
# -----------------------------------------------------------------------------
class Conductor(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario conductor",
        on_delete=models.PROTECT,
        related_name="conductor",
        limit_choices_to={"rol": Usuario.Rol.CONDUCTOR},
    )
    folio_conatacoch = models.CharField("folio CONATACOCH", max_length=20, db_index=True)
    vehiculo = models.ForeignKey(
        Vehiculo,
        verbose_name="vehiculo",
        on_delete=models.PROTECT,
        related_name="conductores",
    )
    en_turno = models.BooleanField("en turno", default=False, db_index=True)
    cupos_disponibles = models.PositiveSmallIntegerField(
        "cupos disponibles", default=0, validators=[MaxValueValidator(30)]
    )
    # Secreto TOTP cifrado (Fernet); nunca se expone por la API.
    otp_secreto = models.CharField("secreto OTP cifrado", max_length=255, blank=True, default="")
    # Codigo OTP temporal para 2FA (inicio de turno). Almacenado en claro
    # solo por corto plazo; se invalida tras usarse o expirar.
    otp_codigo = models.CharField("codigo OTP temporal", max_length=10, blank=True, default="")
    otp_codigo_expira = models.DateTimeField("expiracion OTP", null=True, blank=True)
    # Se almacena el hash SHA-256 del token, nunca el token en claro.
    token_sesion_activa = models.CharField(
        "hash token de sesion", max_length=128, blank=True, default=""
    )

    class Meta:
        db_table = "conductor"
        verbose_name = "conductor"
        verbose_name_plural = "conductores"
        ordering = ["folio_conatacoch"]
        indexes = [
            models.Index(fields=["folio_conatacoch"], name="idx_conductor_folio"),
            models.Index(fields=["en_turno", "folio_conatacoch"], name="idx_conductor_turno"),
            models.Index(fields=["vehiculo", "en_turno"], name="idx_conductor_vehiculo"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cupos_disponibles__gte=0)
                & models.Q(cupos_disponibles__lte=30),
                name="chk_conductor_cupos",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.folio_conatacoch} - {self.usuario.nombre}"

    def set_otp_secreto(self, valor_plano: str) -> None:
        self.otp_secreto = cifrar_secreto(valor_plano)

    def get_otp_secreto(self) -> str:
        return descifrar_secreto(self.otp_secreto)

    def set_token_sesion(self, token_plano: str) -> None:
        self.token_sesion_activa = hashlib.sha256(token_plano.encode("utf-8")).hexdigest()

    def clear_token_sesion(self) -> None:
        self.token_sesion_activa = ""


# -----------------------------------------------------------------------------
# Paradero
# -----------------------------------------------------------------------------
class Paradero(models.Model):
    nombre = models.CharField("nombre", max_length=160)
    comuna = models.CharField("comuna", max_length=100, db_index=True)  # Indice B-Tree
    latitud = models.DecimalField("latitud", max_digits=9, decimal_places=6)
    longitud = models.DecimalField("longitud", max_digits=9, decimal_places=6)
    linea = models.ForeignKey(
        LineaColectiva,
        verbose_name="linea",
        on_delete=models.PROTECT,
        related_name="paraderos",
    )

    class Meta:
        db_table = "paradero"
        verbose_name = "paradero"
        verbose_name_plural = "paraderos"
        ordering = ["comuna", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["linea", "nombre"], name="uq_paradero_linea_nombre"
            ),
            models.CheckConstraint(
                condition=models.Q(latitud__gte=-90) & models.Q(latitud__lte=90),
                name="chk_paradero_latitud",
            ),
            models.CheckConstraint(
                condition=models.Q(longitud__gte=-180) & models.Q(longitud__lte=180),
                name="chk_paradero_longitud",
            ),
        ]
        indexes = [
            models.Index(fields=["comuna", "linea"], name="idx_paradero_comuna_linea"),
            models.Index(fields=["latitud", "longitud"], name="idx_paradero_geo"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} - {self.comuna}"


# -----------------------------------------------------------------------------
# TransaccionPago
# -----------------------------------------------------------------------------
class TransaccionPago(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        ANULADO = "ANULADO", "Anulado"
        EXPIRADO = "EXPIRADO", "Expirado"

    codigo_qr_uuid = models.UUIDField(
        "codigo QR",
        default=uuid.uuid4,
        unique=True,  # Indice B-Tree unico
        editable=False,
    )
    pasajero = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="pasajero",
        on_delete=models.PROTECT,  # ON DELETE RESTRICT
        related_name="pagos_realizados",
        limit_choices_to={"rol": Usuario.Rol.CLIENTE},
    )
    conductor = models.ForeignKey(
        Conductor,
        verbose_name="conductor",
        on_delete=models.PROTECT,  # ON DELETE RESTRICT
        related_name="transacciones",
    )
    linea = models.ForeignKey(
        LineaColectiva,
        verbose_name="linea",
        on_delete=models.PROTECT,  # ON DELETE RESTRICT
        related_name="transacciones",
    )
    monto = models.DecimalField(
        "monto (CLP)",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    fecha_hora = models.DateTimeField("fecha y hora", default=timezone.now, db_index=True)
    estado = models.CharField(
        "estado", max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )

    class Meta:
        db_table = "transaccion_pago"
        verbose_name = "transaccion de pago"
        verbose_name_plural = "transacciones de pago"
        ordering = ["-fecha_hora"]
        indexes = [
            models.Index(fields=["conductor", "fecha_hora"], name="idx_pago_conductor_fecha"),
            models.Index(fields=["linea", "fecha_hora"], name="idx_pago_linea_fecha"),
            models.Index(fields=["pasajero", "fecha_hora"], name="idx_pago_pasajero_fecha"),
            models.Index(fields=["estado", "fecha_hora"], name="idx_pago_estado_fecha"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gte=0), name="chk_pago_monto_positivo"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.codigo_qr_uuid} - {self.monto} ({self.estado})"
