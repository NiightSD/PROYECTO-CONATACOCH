"""
Genera datos sinteticos para la prueba de carga de Fase 2.

Uso:
    python manage.py seed_carga --conductores 50 --pasajeros 100

Crea (idempotente):
  * 1 usuario ADMIN, 1 CONDUCTOR y 1 CLIENTE con las credenciales que usa
    ``tests/test_carga.py`` (admin@test.cl, conductor@test.cl, cliente@test.cl).
  * N conductores ``cargaNN@test.cl`` con vehiculo propio, turno activo y
    cupos disponibles, todos asignados a ``linea_id=1``.
  * M pasajeros ``pasajeroNNN@test.cl``.

Este comando es SOLO para entornos de prueba/benchmark local.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Conductor, LineaColectiva, Usuario, Vehiculo

PASSWORD_CARGA = "CargaPass123!"
PASSWORD_CLIENTE = "CargaPass123!"
PASSWORD_CONDUCTOR_DEMO = "ConducPass123!"
PASSWORD_CLIENTE_DEMO = "PasajeroPass123!"
PASSWORD_ADMIN_DEMO = "AdminPass123!"


def _dv_rut(cuerpo: int) -> str:
    """Calcula el digito verificador (modulo 11) de un RUT chileno."""
    suma = 0
    factor = 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def _rut(cuerpo: int) -> str:
    return f"{cuerpo}-{_dv_rut(cuerpo)}"


class Command(BaseCommand):
    help = "Crea usuarios/vehiculos sinteticos para la prueba de carga."

    def add_arguments(self, parser):
        parser.add_argument("--conductores", type=int, default=50)
        parser.add_argument("--pasajeros", type=int, default=100)
        parser.add_argument(
            "--linea-id",
            type=int,
            default=1,
            help="Linea a la que se asignan los vehiculos (default: 1).",
        )

    def _upsert(self, *, email, rut, nombre, password, rol):
        usuario, _ = Usuario.objects.update_or_create(
            email=email,
            defaults={
                "rut": rut,
                "nombre": nombre,
                "rol": rol,
                "activo": True,
                "intentos_fallidos": 0,
                "bloqueado_hasta": None,
            },
        )
        usuario.set_password(password)
        usuario.save(update_fields=["password"])
        return usuario

    @transaction.atomic
    def handle(self, *args, **options):
        num_conductores = options["conductores"]
        num_pasajeros = options["pasajeros"]
        linea_id = options["linea_id"]

        try:
            linea = LineaColectiva.objects.get(id=linea_id)
        except LineaColectiva.DoesNotExist as exc:
            raise CommandError(
                f"La linea id={linea_id} no existe. Ejecute seed_conatacoch primero."
            ) from exc

        # Cuentas demo compatibles con tests/test_carga.py y con la suite.
        self._upsert(
            email="admin@test.cl",
            rut="19000001-4",
            nombre="Admin Carga",
            password=PASSWORD_ADMIN_DEMO,
            rol=Usuario.Rol.ADMIN,
        )
        self._upsert(
            email="conductor@test.cl",
            rut="19000002-2",
            nombre="Conductor Demo Carga",
            password=PASSWORD_CONDUCTOR_DEMO,
            rol=Usuario.Rol.CONDUCTOR,
        )
        self._upsert(
            email="cliente@test.cl",
            rut="19000003-0",
            nombre="Cliente Demo Carga",
            password=PASSWORD_CLIENTE_DEMO,
            rol=Usuario.Rol.CLIENTE,
        )

        # Un conductor "demo" con vehiculo y turno para los flujos existentes.
        usuario_demo = Usuario.objects.get(email="conductor@test.cl")
        vehiculo_demo, _ = Vehiculo.objects.update_or_create(
            patente="DEMO-01",
            defaults={
                "marca_modelo": "Demo",
                "capacidad_pasajeros": 4,
                "linea": linea,
            },
        )
        Conductor.objects.update_or_create(
            usuario=usuario_demo,
            defaults={
                "folio_conatacoch": "900001",
                "vehiculo": vehiculo_demo,
                "en_turno": True,
                "cupos_disponibles": 4,
            },
        )

        creados_c = 0
        for indice in range(1, num_conductores + 1):
            email = f"carga{indice:02d}@test.cl"
            rut = _rut(20000000 + indice)
            usuario = self._upsert(
                email=email,
                rut=rut,
                nombre=f"Conductor Carga {indice:02d}",
                password=PASSWORD_CARGA,
                rol=Usuario.Rol.CONDUCTOR,
            )
            vehiculo, _ = Vehiculo.objects.update_or_create(
                patente=f"CA-{indice:04d}",
                defaults={
                    "marca_modelo": "Sintetico",
                    "capacidad_pasajeros": 4,
                    "linea": linea,
                },
            )
            Conductor.objects.update_or_create(
                usuario=usuario,
                defaults={
                    "folio_conatacoch": f"8{indice:05d}",
                    "vehiculo": vehiculo,
                    "en_turno": True,
                    "cupos_disponibles": 4,
                },
            )
            creados_c += 1

        creados_p = 0
        for indice in range(1, num_pasajeros + 1):
            self._upsert(
                email=f"pasajero{indice:03d}@test.cl",
                rut=_rut(30000000 + indice),
                nombre=f"Pasajero Carga {indice:03d}",
                password=PASSWORD_CLIENTE,
                rol=Usuario.Rol.CLIENTE,
            )
            creados_p += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"[seed_carga] OK linea={linea.id} "
                f"conductores={creados_c} pasajeros={creados_p} "
                f"password={PASSWORD_CARGA}"
            )
        )
