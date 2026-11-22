"""
Pruebas de carga y rendimiento en vivo (Fase 2) - CONATACOCH.

Escenarios:
  * 50 conductores sinteticos, cada uno con su PROPIO vehiculo, enviando
    telemetria GPS de forma concurrente.
  * 100 pasajeros sinteticos consultando el calculo dinamico de ETA de forma
    concurrente.

Metricas:
  * Latencia promedio, p95 y p99 (ms).
  * Throughput real = total_requests / tiempo_total_de_reloj (req/s).
  * Distribucion de codigos HTTP y validaciones de correctitud.

Requisitos:
  * Servidor Django en ejecucion (``runserver 127.0.0.1:8000``).
  * ``python manage.py seed_conatacoch`` y ``python manage.py seed_carga``.
  * ``MONGO_MOCK=1`` para ejecutar sin un MongoDB real.
  * ``THROTTLE_ANON`` suficientemente alto: la prueba realiza 150 logins
    desde la misma IP (p. ej. ``THROTTLE_ANON=1000/min``).

Uso:
    BASE_URL=http://127.0.0.1:8000 python tests/test_carga.py

El script NO es una prueba de pytest (no define funciones ``test_*``); se
ejecuta directamente contra un servidor vivo.
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import httpx

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = float(os.getenv("CARGA_TIMEOUT", "60"))
MAX_WORKERS_GPS = int(os.getenv("CARGA_WORKERS_GPS", "50"))
MAX_WORKERS_ETA = int(os.getenv("CARGA_WORKERS_ETA", "100"))

# Credenciales creadas por ``manage.py seed_carga``.
PASSWORD_CONDUCTOR = "ConducPass123!"
PASSWORD_PASAJERO = "PasajeroPass123!"
EMAILS_CONDUCTORES = [f"carga{i:02d}@test.cl" for i in range(1, 51)]
EMAILS_PASAJEROS = [f"pasajero{i:03d}@test.cl" for i in range(1, 101)]


# -----------------------------------------------------------------------------
# Metricas
# -----------------------------------------------------------------------------
def percentil(valores: list[float], p: float) -> float:
    """Percentil por interpolacion lineal (p en 0..100)."""
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return ordenados[0]
    rango = (len(ordenados) - 1) * (p / 100.0)
    bajo = math.floor(rango)
    alto = math.ceil(rango)
    if bajo == alto:
        return ordenados[int(rango)]
    peso = rango - bajo
    return ordenados[bajo] * (1.0 - peso) + ordenados[alto] * peso


def medir_latencia(func, *args, **kwargs):
    """Ejecuta una funcion y retorna (latencia_ms, status_code, respuesta)."""
    inicio = time.perf_counter()
    try:
        resultado = func(*args, **kwargs)
        status = resultado.status_code
        try:
            contenido = resultado.json() if resultado.content else {}
        except ValueError:
            contenido = {"raw": resultado.text[:300]}
    except Exception as exc:  # timeout, conexion rechazada, etc.
        status = 0
        contenido = {"error": f"{type(exc).__name__}: {exc}"}
    fin = time.perf_counter()
    return (fin - inicio) * 1000.0, status, contenido


class MedidorCarga:
    """Acumula latencias y codigos HTTP de una fase de carga."""

    def __init__(self):
        self.latencias: list[float] = []
        self.status_codes: dict[int, int] = {}
        self.exitos = 0
        self.errores = 0

    def agregar(self, latencia_ms: float, status_code: int) -> None:
        self.latencias.append(latencia_ms)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        if 200 <= status_code < 300:
            self.exitos += 1
        else:
            self.errores += 1

    def resumen(self, nombre: str, duracion_segundos: float) -> dict:
        total = len(self.latencias)
        throughput = total / duracion_segundos if duracion_segundos > 0 else 0.0
        return {
            "nombre": nombre,
            "total_requests": total,
            "exitos": self.exitos,
            "errores": self.errores,
            "promedio_ms": round(statistics.mean(self.latencias), 2)
            if self.latencias
            else 0.0,
            "p95_ms": round(percentil(self.latencias, 95), 2),
            "p99_ms": round(percentil(self.latencias, 99), 2),
            "min_ms": round(min(self.latencias), 2) if self.latencias else 0.0,
            "max_ms": round(max(self.latencias), 2) if self.latencias else 0.0,
            "duracion_segundos": round(duracion_segundos, 3),
            "throughput_rps": round(throughput, 2),
            "status_codes": dict(sorted(self.status_codes.items())),
        }


# -----------------------------------------------------------------------------
# Cliente HTTP / autenticacion
# -----------------------------------------------------------------------------
def crear_cliente_http() -> httpx.Client:
    """Cliente con pool amplio para soportar 100+ conexiones concurrentes."""
    return httpx.Client(
        timeout=TIMEOUT,
        limits=httpx.Limits(max_connections=250, max_keepalive_connections=150),
        headers={"Accept": "application/json"},
    )


def obtener_token(cliente: httpx.Client, email: str, password: str, rol: str) -> str:
    """Autentica una cuenta y retorna su access token JWT."""
    resp = cliente.post(
        f"{BASE_URL}/api/auth/login/",
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    if resp.status_code == 429:
        raise RuntimeError(
            "Login rechazado por throttling (HTTP 429). Reinicie el servidor con "
            "THROTTLE_ANON=1000/min y THROTTLE_USER=10000/min para la prueba de carga."
        )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Login fallido para {email} ({rol}): HTTP {resp.status_code} "
            f"{resp.text[:300]}"
        )
    return resp.json()["access"]


def autenticar_lote(
    cliente: httpx.Client,
    cuentas: list[tuple[str, str, str]],
    etiqueta: str,
) -> list[str]:
    """Autentica secuencialmente un lote de cuentas (evita locks de SQLite)."""
    print(f"\n[login] Autenticando {len(cuentas)} {etiqueta}...")
    inicio = time.perf_counter()
    tokens: list[str] = []
    for indice, (email, password, rol) in enumerate(cuentas, start=1):
        tokens.append(obtener_token(cliente, email, password, rol))
        if indice % 25 == 0 or indice == len(cuentas):
            print(f"[login]   {indice}/{len(cuentas)} {etiqueta} autenticados")
    duracion = time.perf_counter() - inicio
    print(f"[login] {len(tokens)} {etiqueta} listos en {duracion:.2f}s")
    return tokens


# -----------------------------------------------------------------------------
# Tareas de carga
# -----------------------------------------------------------------------------
def enviar_gps_un_vehiculo(cliente: httpx.Client, token: str, indice: int):
    """Simula un vehiculo enviando un punto de telemetria GPS."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "latitud": -33.4489 + (indice * 0.0001),
        "longitud": -70.6693 + (indice * 0.0001),
        "velocidad_kmh": 40.0 + (indice % 30),
        "rumbo": 180.0,
        "cupos_disponibles": 4,
    }
    return medir_latencia(
        cliente.post,
        f"{BASE_URL}/api/telemetria/enviar/",
        json=payload,
        headers=headers,
        timeout=TIMEOUT,
    )


def consultar_eta_un_pasajero(cliente: httpx.Client, token: str, indice: int):
    """Simula un pasajero consultando el ETA de la linea 1."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "linea_id": 1,
        "latitud_pasajero": -33.4489 + (indice * 0.0001),
        "longitud_pasajero": -70.6693 + (indice * 0.0001),
    }
    return medir_latencia(
        cliente.post,
        f"{BASE_URL}/api/eta/calcular/",
        json=payload,
        headers=headers,
        timeout=TIMEOUT,
    )


def ejecutar_fase_concurrente(
    cliente: httpx.Client,
    nombre: str,
    descripcion: str,
    tokens: list[str],
    tarea,
    max_workers: int,
) -> tuple[dict, list[tuple[int, int, dict]]]:
    """Ejecuta N tareas concurrentes y calcula metricas con reloj de pared."""
    print(f"\n{'=' * 68}")
    print(f"PRUEBA DE CARGA: {descripcion}")
    print(f"Concurrencia: {max_workers} workers | Requests: {len(tokens)}")
    print(f"{'=' * 68}")

    medidor = MedidorCarga()
    resultados: list[tuple[int, int, dict]] = []

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {
            executor.submit(tarea, cliente, token, indice): indice
            for indice, token in enumerate(tokens)
        }
        for futuro in as_completed(futuros):
            indice = futuros[futuro]
            try:
                latencia, status, contenido = futuro.result()
            except Exception as exc:
                latencia, status, contenido = (
                    0.0,
                    0,
                    {"error": f"{type(exc).__name__}: {exc}"},
                )
            medidor.agregar(latencia, status)
            resultados.append((indice, status, contenido))
    duracion = time.perf_counter() - inicio

    res = medidor.resumen(nombre, duracion)
    print(f"Requests totales:      {res['total_requests']}")
    print(f"Exitosos (2xx):        {res['exitos']}")
    print(f"Errores:               {res['errores']}")
    print(f"Latencia promedio:     {res['promedio_ms']} ms")
    print(f"Latencia p95:          {res['p95_ms']} ms")
    print(f"Latencia p99:          {res['p99_ms']} ms")
    print(f"Latencia min/max:      {res['min_ms']} / {res['max_ms']} ms")
    print(f"Duracion (reloj):      {res['duracion_segundos']} s")
    print(f"Throughput:            {res['throughput_rps']} req/s")
    print(f"Codigos HTTP:          {res['status_codes']}")
    return res, resultados


def _muestras_errores(resultados, limite: int = 3) -> list[dict]:
    muestras = []
    for indice, status, contenido in resultados:
        if not (200 <= status < 300):
            muestras.append({"indice": indice, "status": status, "respuesta": contenido})
        if len(muestras) >= limite:
            break
    return muestras


# -----------------------------------------------------------------------------
# Escenarios
# -----------------------------------------------------------------------------
def ejecutar_prueba_carga_telemetria(
    cliente: httpx.Client, tokens: list[str]
) -> dict:
    """50 vehiculos distintos enviando GPS concurrentemente."""
    res, resultados = ejecutar_fase_concurrente(
        cliente,
        nombre="telemetria_gps",
        descripcion=f"{len(tokens)} vehiculos distintos enviando GPS",
        tokens=tokens,
        tarea=enviar_gps_un_vehiculo,
        max_workers=MAX_WORKERS_GPS,
    )

    ids_vehiculos = {
        contenido.get("id_vehiculo")
        for _, status, contenido in resultados
        if status == 201
        and isinstance(contenido, dict)
        and contenido.get("id_vehiculo") is not None
    }
    res["vehiculos_distintos_detectados"] = len(ids_vehiculos)
    res["vehiculos_esperados"] = len(tokens)
    res["validacion_vehiculos_unicos"] = len(ids_vehiculos) == len(tokens)
    res["errores_muestra"] = _muestras_errores(resultados)

    print(f"Vehiculos distintos:   {len(ids_vehiculos)}/{len(tokens)}")
    print(f"IDs unicos validados:  {res['validacion_vehiculos_unicos']}")
    if res["errores_muestra"]:
        print(f"Muestras de error:     {res['errores_muestra']}")
    return res


def ejecutar_prueba_carga_eta(cliente: httpx.Client, tokens: list[str]) -> dict:
    """100 pasajeros consultando ETA concurrentemente."""
    res, resultados = ejecutar_fase_concurrente(
        cliente,
        nombre="eta_pasajeros",
        descripcion=f"{len(tokens)} pasajeros consultando ETA",
        tokens=tokens,
        tarea=consultar_eta_un_pasajero,
        max_workers=MAX_WORKERS_ETA,
    )

    opciones = [
        len(contenido.get("opciones") or [])
        for _, status, contenido in resultados
        if status == 200 and isinstance(contenido, dict)
    ]
    res["eta_opciones_min"] = min(opciones) if opciones else 0
    res["eta_opciones_max"] = max(opciones) if opciones else 0
    res["eta_respuestas_con_opciones"] = sum(1 for n in opciones if n > 0)
    res["errores_muestra"] = _muestras_errores(resultados)

    print(f"Opciones ETA min/max:  {res['eta_opciones_min']} / {res['eta_opciones_max']}")
    print(f"Respuestas con flota:  {res['eta_respuestas_con_opciones']}/{len(tokens)}")
    if res["errores_muestra"]:
        print(f"Muestras de error:     {res['errores_muestra']}")
    return res


# -----------------------------------------------------------------------------
# Orquestacion
# -----------------------------------------------------------------------------
def verificar_servidor(cliente: httpx.Client) -> None:
    """Comprueba que el servidor este vivo antes de autenticar 150 cuentas."""
    try:
        resp = cliente.get(f"{BASE_URL}/api/health/live/", timeout=10.0)
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo conectar a {BASE_URL}. Levante runserver primero. ({exc})"
        ) from exc
    if resp.status_code != 200:
        raise RuntimeError(
            f"Health check fallo: HTTP {resp.status_code} {resp.text[:200]}"
        )
    print(f"[health] Servidor disponible en {BASE_URL}")


def ejecutar_todas_pruebas() -> dict:
    """Ejecuta todas las pruebas de carga y retorna metricas serializables."""
    resultados: dict = {
        "entorno": {
            "base_url": BASE_URL,
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "concurrencia_gps": MAX_WORKERS_GPS,
            "concurrencia_eta": MAX_WORKERS_ETA,
            "timeout_segundos": TIMEOUT,
            "nota": (
                "Validacion local con SQLite y MONGO_MOCK=1; latencias incluyen "
                "cliente HTTP, servidor Django de desarrollo y GIL de Python."
            ),
        }
    }

    print("\n" + "=" * 68)
    print("CONATACOCH - Pruebas de Carga Fase 2")
    print(f"Fecha UTC: {resultados['entorno']['fecha_utc']}")
    print(f"Servidor:  {BASE_URL}")
    print("=" * 68)

    with crear_cliente_http() as cliente:
        verificar_servidor(cliente)

        cuentas_conductores = [
            (email, PASSWORD_CONDUCTOR, "CONDUCTOR") for email in EMAILS_CONDUCTORES
        ]
        cuentas_pasajeros = [
            (email, PASSWORD_PASAJERO, "CLIENTE") for email in EMAILS_PASAJEROS
        ]

        inicio_login = time.perf_counter()
        tokens_conductores = autenticar_lote(
            cliente, cuentas_conductores, "conductores"
        )
        tokens_pasajeros = autenticar_lote(
            cliente, cuentas_pasajeros, "pasajeros"
        )
        resultados["entorno"]["duracion_logins_segundos"] = round(
            time.perf_counter() - inicio_login, 3
        )

        resultados["telemetria_gps"] = ejecutar_prueba_carga_telemetria(
            cliente, tokens_conductores
        )
        resultados["eta_pasajeros"] = ejecutar_prueba_carga_eta(
            cliente, tokens_pasajeros
        )

    print("\n" + "=" * 68)
    print("RESUMEN FINAL DE METRICAS")
    print("=" * 68)
    for clave in ("telemetria_gps", "eta_pasajeros"):
        res = resultados[clave]
        print(f"\n--- {res['nombre']} ---")
        print(f"  Requests:    {res['total_requests']}")
        print(f"  Exitosos:    {res['exitos']}")
        print(f"  Errores:     {res['errores']}")
        print(f"  Promedio:    {res['promedio_ms']} ms")
        print(f"  p95:         {res['p95_ms']} ms")
        print(f"  p99:         {res['p99_ms']} ms")
        print(f"  Throughput:  {res['throughput_rps']} req/s")
        print(f"  HTTP:        {res['status_codes']}")

    # Bloque JSON listo para adjuntar al informe tecnico.
    print("\n" + "=" * 68)
    print("METRICAS_JSON")
    print("=" * 68)
    print(json.dumps(resultados, indent=2, ensure_ascii=False, default=str))

    salida = os.getenv("CARGA_OUTPUT")
    if salida:
        with open(salida, "w", encoding="utf-8") as archivo:
            json.dump(resultados, archivo, indent=2, ensure_ascii=False, default=str)
        print(f"\n[ok] Metricas guardadas en {salida}")

    return resultados


def _validar_resultados(resultados: dict) -> list[str]:
    problemas = []
    gps = resultados["telemetria_gps"]
    eta = resultados["eta_pasajeros"]
    if gps["errores"]:
        problemas.append(f"Telemetria: {gps['errores']} requests no exitosos")
    if not gps.get("validacion_vehiculos_unicos"):
        problemas.append(
            "Telemetria: no se confirmaron 50 vehiculos distintos "
            f"({gps.get('vehiculos_distintos_detectados')}/{gps.get('vehiculos_esperados')})"
        )
    if eta["errores"]:
        problemas.append(f"ETA: {eta['errores']} requests no exitosos")
    if eta.get("eta_respuestas_con_opciones", 0) != eta["total_requests"]:
        problemas.append(
            "ETA: algunas respuestas no incluyeron opciones de flota "
            f"({eta.get('eta_respuestas_con_opciones')}/{eta['total_requests']})"
        )
    return problemas


if __name__ == "__main__":
    try:
        metricas = ejecutar_todas_pruebas()
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    problemas = _validar_resultados(metricas)
    if problemas:
        print("\n[FALLO] Validaciones de carga:", file=sys.stderr)
        for problema in problemas:
            print(f"  - {problema}", file=sys.stderr)
        raise SystemExit(1)

    print("\n[OK] Pruebas de carga completadas sin errores.")
