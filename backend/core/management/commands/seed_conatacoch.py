"""
Carga inicial idempotente de CONATACOCH (Fase 1).

Uso:
    python manage.py seed_conatacoch
    python manage.py seed_conatacoch --data-file /app/data/recorridos.json
    python manage.py seed_conatacoch --skip-paraderos

Garantias:
  * update_or_create por clave natural => puede ejecutarse N veces sin duplicar.
  * Lee el dataset oficial de recorridos (660 itinerarios, Region 13).
  * Crea paraderos base georreferenciados para cada recorrido.
  * Crea usuarios/vehiculos/conductores/clientes demo con passwords Argon2id.
  * Secretos TOTP cifrados y token de sesion hasheado (nunca texto plano).
  * Intenta crear los indices 2dsphere/TTL de MongoDB (Atlas o fallback local).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import unicodedata
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from core.models import (
    Cliente,
    Conductor,
    LineaColectiva,
    Paradero,
    Usuario,
    Vehiculo,
)

# Coordenadas aproximadas de las comunas de la Region Metropolitana.
# Se usan como centro de los paraderos base (no reemplazan geocodificacion).
COMUNAS_RM: dict[str, tuple[float, float]] = {
    "Buin": (-33.7333, -70.7500),
    "Calera de Tango": (-33.6667, -70.7833),
    "Cerrillos": (-33.5028, -70.7117),
    "Cerro Navia": (-33.4244, -70.7239),
    "Colina": (-33.2022, -70.6747),
    "Curacavi": (-33.4028, -71.1444),
    "El Bosque": (-33.5647, -70.6758),
    "El Monte": (-33.6811, -70.9864),
    "Estacion Central": (-33.4569, -70.7003),
    "Huechuraba": (-33.3667, -70.6667),
    "Independencia": (-33.4167, -70.6667),
    "Isla de Maipo": (-33.7500, -70.9000),
    "La Cisterna": (-33.5333, -70.6667),
    "La Florida": (-33.5167, -70.5833),
    "La Granja": (-33.5333, -70.6333),
    "La Pintana": (-33.5833, -70.6333),
    "La Reina": (-33.4500, -70.5500),
    "Lampa": (-33.2833, -70.8833),
    "Las Condes": (-33.4167, -70.5833),
    "Lo Barnechea": (-33.3500, -70.5167),
    "Lo Espejo": (-33.5167, -70.7000),
    "Lo Prado": (-33.4500, -70.7167),
    "Macul": (-33.5000, -70.6000),
    "Maipu": (-33.5167, -70.7667),
    "Maria Pinto": (-33.5167, -71.1167),
    "Melipilla": (-33.6858, -71.2164),
    "Padre Hurtado": (-33.5667, -70.8167),
    "Paine": (-33.8167, -70.7500),
    "Pedro Aguirre Cerda": (-33.5000, -70.6667),
    "Penaflor": (-33.6167, -70.8833),
    "Penalolen": (-33.4833, -70.5500),
    "Pirque": (-33.6333, -70.5833),
    "Providencia": (-33.4333, -70.6167),
    "Pudahuel": (-33.4333, -70.7667),
    "Puente Alto": (-33.6167, -70.5833),
    "Quilicura": (-33.3667, -70.7333),
    "Quinta Normal": (-33.4333, -70.7000),
    "Recoleta": (-33.4167, -70.6333),
    "Renca": (-33.4000, -70.7167),
    "San Bernardo": (-33.6000, -70.7000),
    "San Joaquin": (-33.5000, -70.6333),
    "San Jose de Maipo": (-33.6333, -70.3500),
    "San Miguel": (-33.5000, -70.6500),
    "San Ramon": (-33.5333, -70.6500),
    "Santiago": (-33.4489, -70.6693),
    "Talagante": (-33.6667, -70.9333),
    "Vitacura": (-33.3833, -70.5833),
    "Nunoa": (-33.4500, -70.6000),
}

CENTRO_FALLBACK = ("Santiago", (-33.4489, -70.6693))

DATASET_NAME = "recorridos_conatacoch_taxi_colectivo_2.json"

CREDENCIALES_DEMO = {
    "admin": ("11.111.111-1", "admin@conatacoch.cl", "AdminConata2026!"),
    "conductor1": ("22.222.222-2", "conductor1@conatacoch.cl", "Conduc2026!"),
    "conductor2": ("33.333.333-3", "conductor2@conatacoch.cl", "Conduc2026!"),
    "pasajero1": ("44.444.444-4", "pasajero1@conatacoch.cl", "Pasajero2026!"),
    "pasajero2": ("55.555.555-5", "pasajero2@conatacoch.cl", "Pasajero2026!"),
}

# Datos verosimiles para que las tablas se vean reales en phpMyAdmin.
NOMBRES_DEMO = {
    "admin": "Camila Rojas Contreras",
    "conductor1": "Jorge Fuentes Sepúlveda",
    "conductor2": "Luis Herrera Molina",
    "pasajero1": "Valentina Soto Muñoz",
    "pasajero2": "Diego Ramírez Vera",
}

PERFILES_CLIENTE = {
    "pasajero1": {
        "telefono": "+569 8123 4567",
        "direccion": "Av. Vicuña Mackenna 1420",
        "comuna": "Santiago",
    },
    "pasajero2": {
        "telefono": "+569 7766 5544",
        "direccion": "Gran Avenida 9080",
        "comuna": "La Florida",
    },
}


def _sin_acentos(valor: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(valor))
    return "".join(c for c in normalizado if not unicodedata.combining(c)).strip().lower()


COMUNAS_NORM = {_sin_acentos(nombre): valor for nombre, valor in COMUNAS_RM.items()}


def _coordenadas(comuna: str) -> tuple[float, float]:
    return COMUNAS_NORM.get(_sin_acentos(comuna), CENTRO_FALLBACK[1])


def _jitter(clave: str) -> tuple[float, float]:
    """Desplazamiento deterministico (~1 km) para no superponer paraderos."""
    digest = hashlib.sha256(clave.encode("utf-8")).digest()
    dlat = (int.from_bytes(digest[0:2], "big") % 2001 - 1000) / 100_000.0
    dlng = (int.from_bytes(digest[2:4], "big") % 2001 - 1000) / 100_000.0
    return dlat, dlng


def _decimal6(valor: float) -> Decimal:
    return Decimal(str(round(valor, 6)))


def _texto(fila: dict, clave: str, max_len: int) -> str:
    return str(fila.get(clave, "") or "").strip()[:max_len]


class Command(BaseCommand):
    help = "Carga idempotente del dataset de recorridos, paraderos y usuarios demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-file",
            default=os.getenv("SEED_DATA_FILE", ""),
            help="Ruta al JSON de recorridos (default: SEED_DATA_FILE o dataset del repo).",
        )
        parser.add_argument(
            "--skip-paraderos",
            action="store_true",
            help="No genera paraderos base (util para cargas rapidas).",
        )
        parser.add_argument(
            "--skip-usuarios",
            action="store_true",
            help="No crea usuarios/vehiculos/conductores demo.",
        )
        parser.add_argument(
            "--tarifa-urbana",
            type=int,
            default=int(os.getenv("SEED_TARIFA_URBANA", "1000")),
            help="Tarifa demo para servicios urbanos (CLP).",
        )
        parser.add_argument(
            "--tarifa-rural",
            type=int,
            default=int(os.getenv("SEED_TARIFA_RURAL", "1500")),
            help="Tarifa demo para servicios rurales (CLP).",
        )

    # ------------------------------------------------------------------ utils
    def _resolver_dataset(self, ruta_explicita: str) -> Path:
        candidatos = [
            ruta_explicita,
            os.getenv("SEED_DATA_FILE", ""),
            str(settings.BASE_DIR / "data" / DATASET_NAME),
            str(settings.BASE_DIR.parent / DATASET_NAME),
            str(settings.BASE_DIR.parent / "data" / DATASET_NAME),
        ]
        for candidato in candidatos:
            if not candidato:
                continue
            ruta = Path(candidato)
            if ruta.is_file():
                return ruta
        raise CommandError(
            "No se encontro el dataset. Coloque "
            f"'{DATASET_NAME}' en la raiz del repo o defina SEED_DATA_FILE."
        )

    def _leer_dataset(self, ruta: Path) -> list[dict]:
        try:
            with ruta.open("r", encoding="utf-8-sig") as archivo:
                datos = json.load(archivo)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"No se pudo leer {ruta}: {exc}") from exc

        if not isinstance(datos, list) or not datos:
            raise CommandError(f"El dataset {ruta} no es una lista JSON con datos.")
        return datos

    # ------------------------------------------------------------------- lineas
    def _cargar_lineas(self, filas: list[dict], tarifa_urbana: int, tarifa_rural: int) -> tuple[int, int]:
        creadas = actualizadas = 0

        for indice, fila in enumerate(filas, start=1):
            try:
                region = int(fila["REGION"])
                folio = int(fila["FOLIO"])
                nombre_recorrido = _texto(fila, "NOMBRE_RECORRIDO", 50)
            except (KeyError, TypeError, ValueError) as exc:
                raise CommandError(f"Fila {indice} invalida en el dataset: {exc}") from exc

            tipo_servicio = _texto(fila, "TIPO_SERVICIO", 80)
            tipo_trazado = _texto(fila, "TIPO_TRAZADO", 20) or "PRINCIPAL"
            tarifa = Decimal(tarifa_rural if "RURAL" in tipo_servicio.upper() else tarifa_urbana)

            # Clave natural verificada en el dataset: 660 combinaciones unicas.
            _, creada = LineaColectiva.objects.update_or_create(
                folio=folio,
                nombre_recorrido=nombre_recorrido,
                tipo_trazado=tipo_trazado,
                defaults={
                    "region": region,
                    "tipo_servicio": tipo_servicio,
                    "nombre_origen": _texto(fila, "NOMBRE_ORIGEN", 150),
                    "comuna_origen": _texto(fila, "COMUNA_ORIGEN", 100),
                    "domicilio_origen": _texto(fila, "DOMICILIO_ORIGEN", 200),
                    "nombre_destino": _texto(fila, "NOMBRE_DESTINO", 150),
                    "comuna_destino": _texto(fila, "COMUNA_DESTINO", 100),
                    "domicilio_destino": _texto(fila, "DOMICILIO_DESTINO", 200),
                    "tarifa_actual": tarifa,
                },
            )
            if creada:
                creadas += 1
            else:
                actualizadas += 1

            if indice % 100 == 0:
                self.stdout.write(f"[seed] Lineas procesadas: {indice}/{len(filas)}")

        return creadas, actualizadas

    def _linea_demo(self, folio: int) -> LineaColectiva:
        """Recupera o crea la linea asociada a un folio demo."""
        linea = (
            LineaColectiva.objects.filter(folio=folio)
            .order_by("nombre_recorrido")
            .first()
        )
        if linea:
            return linea

        linea, _ = LineaColectiva.objects.update_or_create(
            folio=folio,
            nombre_recorrido="T",
            tipo_trazado=LineaColectiva.TipoTrazado.PRINCIPAL,
            defaults={
                "region": 13,
                "tipo_servicio": LineaColectiva.TipoServicio.URBANO,
                "nombre_origen": "SANTIAGO",
                "comuna_origen": "Santiago",
                "domicilio_origen": "ALAMEDA",
                "nombre_destino": "SANTIAGO",
                "comuna_destino": "Santiago",
                "domicilio_destino": "ALAMEDA",
                "tarifa_actual": Decimal(1000),
            },
        )
        return linea

    # ---------------------------------------------------------------- paraderos
    def _cargar_paraderos(self) -> tuple[int, int]:
        creados = actualizados = 0
        lineas = LineaColectiva.objects.all().iterator(chunk_size=200)
        total = LineaColectiva.objects.count()

        for indice, linea in enumerate(lineas, start=1):
            extremos = (
                ("Origen", linea.comuna_origen, linea.domicilio_origen),
                ("Destino", linea.comuna_destino, linea.domicilio_destino),
            )
            for etiqueta, comuna, domicilio in extremos:
                lat_base, lng_base = _coordenadas(comuna)
                dlat, dlng = _jitter(
                    f"{linea.folio}:{linea.nombre_recorrido}:{etiqueta}:{comuna}"
                )
                nombre = f"{linea.nombre_recorrido} | {etiqueta}: {domicilio}"[:160]
                _, creado = Paradero.objects.update_or_create(
                    linea=linea,
                    nombre=nombre,
                    defaults={
                        "comuna": (comuna or CENTRO_FALLBACK[0])[:100],
                        "latitud": _decimal6(lat_base + dlat),
                        "longitud": _decimal6(lng_base + dlng),
                    },
                )
                if creado:
                    creados += 1
                else:
                    actualizados += 1

            if indice % 100 == 0:
                self.stdout.write(f"[seed] Paraderos base para lineas: {indice}/{total}")

        return creados, actualizados

    # ----------------------------------------------------------------- usuarios
    def _upsert_usuario(
        self,
        *,
        rut: str,
        email: str,
        nombre: str,
        password: str,
        rol: str,
        is_staff: bool = False,
        is_superuser: bool = False,
    ) -> tuple[Usuario, bool]:
        usuario = Usuario.objects.filter(Q(rut=rut) | Q(email=email)).first()
        creado = usuario is None
        if usuario is None:
            usuario = Usuario(rut=rut)

        usuario.email = email
        usuario.nombre = nombre
        usuario.rol = rol
        usuario.activo = True
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.is_staff = is_staff
        usuario.is_superuser = is_superuser
        usuario.set_password(password)
        usuario.save()
        return usuario, creado

    def _generar_otp(self) -> str:
        return base64.b32encode(secrets.token_bytes(10)).decode("ascii").rstrip("=")

    def _cargar_usuarios(self, linea_uno: LineaColectiva, linea_dos: LineaColectiva) -> dict[str, int]:
        stats = {"usuarios": 0, "vehiculos": 0, "conductores": 0, "clientes": 0}

        admin, _ = self._upsert_usuario(
            rut=CREDENCIALES_DEMO["admin"][0],
            email=CREDENCIALES_DEMO["admin"][1],
            nombre=NOMBRES_DEMO["admin"],
            password=CREDENCIALES_DEMO["admin"][2],
            rol=Usuario.Rol.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(f"[seed] Admin asegurado: {admin.email}")
        stats["usuarios"] += 1

        conductor1, _ = self._upsert_usuario(
            rut=CREDENCIALES_DEMO["conductor1"][0],
            email=CREDENCIALES_DEMO["conductor1"][1],
            nombre=NOMBRES_DEMO["conductor1"],
            password=CREDENCIALES_DEMO["conductor1"][2],
            rol=Usuario.Rol.CONDUCTOR,
        )
        conductor2, _ = self._upsert_usuario(
            rut=CREDENCIALES_DEMO["conductor2"][0],
            email=CREDENCIALES_DEMO["conductor2"][1],
            nombre=NOMBRES_DEMO["conductor2"],
            password=CREDENCIALES_DEMO["conductor2"][2],
            rol=Usuario.Rol.CONDUCTOR,
        )
        pasajero1, _ = self._upsert_usuario(
            rut=CREDENCIALES_DEMO["pasajero1"][0],
            email=CREDENCIALES_DEMO["pasajero1"][1],
            nombre=NOMBRES_DEMO["pasajero1"],
            password=CREDENCIALES_DEMO["pasajero1"][2],
            rol=Usuario.Rol.CLIENTE,
        )
        pasajero2, _ = self._upsert_usuario(
            rut=CREDENCIALES_DEMO["pasajero2"][0],
            email=CREDENCIALES_DEMO["pasajero2"][1],
            nombre=NOMBRES_DEMO["pasajero2"],
            password=CREDENCIALES_DEMO["pasajero2"][2],
            rol=Usuario.Rol.CLIENTE,
        )
        stats["usuarios"] += 4

        for clave, usuario in (("pasajero1", pasajero1), ("pasajero2", pasajero2)):
            Cliente.objects.update_or_create(
                usuario=usuario,
                defaults=PERFILES_CLIENTE[clave],
            )
            stats["clientes"] += 1

        vehiculo1, _ = Vehiculo.objects.update_or_create(
            patente="ABCD-12",
            defaults={
                "marca_modelo": "Nissan V16",
                "capacidad_pasajeros": 4,
                "linea": linea_uno,
            },
        )
        vehiculo2, _ = Vehiculo.objects.update_or_create(
            patente="EFGH-34",
            defaults={
                "marca_modelo": "Chevrolet Corsa",
                "capacidad_pasajeros": 4,
                "linea": linea_dos,
            },
        )
        stats["vehiculos"] = 2

        parejas = (
            (conductor1, "234001", vehiculo1),
            (conductor2, "236001", vehiculo2),
        )
        for usuario, folio, vehiculo in parejas:
            conductor, _ = Conductor.objects.update_or_create(
                usuario=usuario,
                defaults={
                    "folio_conatacoch": folio,
                    "vehiculo": vehiculo,
                    "en_turno": True,
                    "cupos_disponibles": vehiculo.capacidad_pasajeros,
                },
            )
            if not conductor.otp_secreto:
                conductor.set_otp_secreto(self._generar_otp())
                conductor.save(update_fields=["otp_secreto"])
            stats["conductores"] += 1

        return stats

    # -------------------------------------------------------------------- main
    def handle(self, *args, **options):
        inicio = time.perf_counter()
        ruta = self._resolver_dataset(options.get("data_file", ""))
        filas = self._leer_dataset(ruta)

        self.stdout.write(self.style.MIGRATE_HEADING("[seed] CONATACOCH - carga inicial idempotente"))
        self.stdout.write(f"[seed] Dataset: {ruta} ({len(filas)} itinerarios)")

        with transaction.atomic():
            lineas_creadas, lineas_actualizadas = self._cargar_lineas(
                filas,
                tarifa_urbana=options["tarifa_urbana"],
                tarifa_rural=options["tarifa_rural"],
            )

            paraderos_creados = paraderos_actualizados = 0
            if not options["skip_paraderos"]:
                paraderos_creados, paraderos_actualizados = self._cargar_paraderos()

            stats_usuarios = {"usuarios": 0, "vehiculos": 0, "conductores": 0, "clientes": 0}
            if not options["skip_usuarios"]:
                linea_uno = self._linea_demo(234001)
                linea_dos = self._linea_demo(236001)
                stats_usuarios = self._cargar_usuarios(linea_uno, linea_dos)

        duracion = round(time.perf_counter() - inicio, 2)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("[seed] Resumen de la carga"))
        self.stdout.write(f"  Lineas creadas      : {lineas_creadas}")
        self.stdout.write(f"  Lineas actualizadas : {lineas_actualizadas}")
        self.stdout.write(f"  Paraderos creados   : {paraderos_creados}")
        self.stdout.write(f"  Paraderos actualizados: {paraderos_actualizados}")
        self.stdout.write(f"  Usuarios demo       : {stats_usuarios['usuarios']}")
        self.stdout.write(f"  Vehiculos demo      : {stats_usuarios['vehiculos']}")
        self.stdout.write(f"  Conductores demo    : {stats_usuarios['conductores']}")
        self.stdout.write(f"  Clientes demo       : {stats_usuarios['clientes']}")
        self.stdout.write(f"  Totales en BD       : lineas={LineaColectiva.objects.count()} "
                          f"paraderos={Paradero.objects.count()} usuarios={Usuario.objects.count()} "
                          f"vehiculos={Vehiculo.objects.count()} conductores={Conductor.objects.count()} "
                          f"clientes={Cliente.objects.count()}")
        self.stdout.write(self.style.SUCCESS(f"[seed] Completado en {duracion}s (idempotente)."))

        if not options["skip_usuarios"]:
            self.stdout.write("")
            self.stdout.write("[seed] Credenciales demo (cambiar en produccion):")
            for clave, (rut, email, password) in CREDENCIALES_DEMO.items():
                self.stdout.write(
                    f"  {clave:<11} nombre={NOMBRES_DEMO[clave]:<28} "
                    f"RUT={rut}  email={email}  password={password}"
                )

        # Indices de telemetria: no abortan el seed si Atlas no responde.
        if not getattr(settings, "MONGO_MOCK", False):
            try:
                from core import mongo

                nombres = mongo.ensure_indexes()
                self.stdout.write(
                    self.style.SUCCESS(
                        "[seed] Indices MongoDB: " + ", ".join(nombres.values())
                    )
                )
            except Exception as exc:  # pragma: no cover - depende de Atlas
                mongo.reset_client()
                self.stdout.write(
                    self.style.WARNING(
                        f"[seed] MongoDB sin indices (revisa MONGO_ATLAS_URI): {exc}"
                    )
                )
