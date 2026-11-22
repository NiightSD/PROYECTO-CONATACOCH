"""
Pruebas de carga y rendimiento (Fase 2):
  * 50 vehiculos enviando GPS simultaneamente (telemetria).
  * 100 pasajeros consultando ETA simultaneamente.
  * Metricas: latencia promedio, p95, throughput.

Usa concurrent.futures.ThreadPoolExecutor + httpx.
Requiere que el servidor Django este corriendo (runserver o test client).
"""
from __future__ import annotations

import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import httpx

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# Credenciales de prueba
CREDENTIALS = {
    "conductor": {"email": "conductor@test.cl", "password": "ConducPass123!"},
    "cliente": {"email": "cliente@test.cl", "password": "PasajeroPass123!"},
    "admin": {"email": "admin@test.cl", "password": "AdminPass123!"},
}

# Cuentas sinteticas creadas por `manage.py seed_carga`.
PASSWORD_CARGA = "CargaPass123!"
EMAILS_CONDUCTORES = [f"carga{i:02d}@test.cl" for i in range(1, 51)]
EMAILS_PASAJEROS = [f"pasajero{i:03d}@test.cl" for i in range(1, 101)]


def medir_latencia(func, *args, **kwargs):
    """Ejecuta una funcion y retorna (latencia_ms, status_code, respuesta)."""
    inicio = time.perf_counter()
    try:
        resultado = func(*args, **kwargs)
        status = resultado.status_code
        contenido = resultado.json() if resultado.content else {}
    except Exception as exc:
        status = 0
        contenido = {"error": str(exc)}
    fin = time.perf_counter()
    return (fin - inicio) * 1000, status, contenido


class MedidorCarga:
    """Almacena metricas de carga."""

    def __init__(self):
        self.latencias = []
        self.errores = 0
        self.exitos = 0
        self.status_codes = {}

    def agregar(self, latencia_ms, status_code):
        self.latencias.append(latencia_ms)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        if 200 <= status_code < 300:
            self.exitos += 1
        else:
            self.errores += 1

    @property
    def promedio_ms(self):
        return statistics.mean(self.latencias) if self.latencias else 0

    @property
    def p95_ms(self):
        if not self.latencias:
            return 0
        ordenadas = sorted(self.latencias)
        idx = int(0.95 * len(ordenadas)) - 1
        return ordenadas[max(idx, 0)]

    @property
    def p99_ms(self):
        if not self.latencias:
            return 0
        ordenadas = sorted(self.latencias)
        idx = int(0.99 * len(ordenadas)) - 1
        return ordenadas[max(idx, 0)]

    @property
    def throughput_rps(self):
        if not self.latencias:
            return 0
        total_seg = sum(self.latencias) / 1000.0
        return len(self.latencias) / total_seg if total_seg > 0 else 0

    def resumen(self, nombre):
        return {
            "nombre": nombre,
            "total": len(self.latencias),
            "exitos": self.exitos,
            "errores": self.errores,
            "promedio_ms": round(self.promedio_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "throughput_rps": round(self.throughput_rps, 2),
            "status_codes": self.status_codes,
        }


def obtener_token(cliente_http, rol):
    """Obtiene un token de acceso JWT."""
    resp = cliente_http.post(
        f"{BASE_URL}/api/auth/login/",
        json=CREDENTIALS[rol],
        timeout=10.0,
    )
    if resp.status_code == 200:
        return resp.json()["access"]
    return None


def obtener_token_email(cliente_http, email, password=PASSWORD_CARGA):
    """Obtiene un token JWT para una cuenta sintetica de carga."""
    resp = cliente_http.post(
        f"{BASE_URL}/api/auth/login/",
        json={"email": email, "password": password},
        timeout=10.0,
    )
    if resp.status_code == 200:
        return resp.json()["access"]
    return None


def enviar_gps_un_vehiculo(cliente_http, token, vehiculo_id, indice):
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
        cliente_http.post,
        f"{BASE_URL}/api/telemetria/enviar/",
        json=payload,
        headers=headers,
        timeout=10.0,
    )


def consultar_eta_un_pasajero(cliente_http, token, indice):
    """Simula un pasajero consultando ETA."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "linea_id": 1,
        "latitud_pasajero": -33.4489 + (indice * 0.0001),
        "longitud_pasajero": -70.6693 + (indice * 0.0001),
    }
    return medir_latencia(
        cliente_http.post,
        f"{BASE_URL}/api/eta/calcular/",
        json=payload,
        headers=headers,
        timeout=10.0,
    )


def ejecutar_prueba_carga_telemetria(num_vehiculos=50):
    """Ejecuta prueba de carga: N vehículos enviando GPS simultáneamente."""
    print(f"\n{'='*60}")
    print(f"PRUEBA DE CARGA: {num_vehiculos} vehículos enviando GPS")
    print(f"{'='*60}")

    medidor = MedidorCarga()

    with httpx.Client(timeout=10.0) as client:
        emails = EMAILS_CONDUCTORES[:num_vehiculos]
        tokens = [obtener_token_email(client, email) for email in emails]
        tokens_validos = [t for t in tokens if t]
        if not tokens_validos:
            # Fallback: usar una sola cuenta demo si no se ejecuto seed_carga.
            token = obtener_token(client, "conductor")
            if not token:
                print("ERROR: No se pudo obtener token de conductor")
                return medidor.resumen("telemetria")
            tokens_validos = [token] * num_vehiculos
        elif len(tokens_validos) < num_vehiculos:
            tokens_validos += [tokens_validos[-1]] * (num_vehiculos - len(tokens_validos))

        def tarea(indice):
            return enviar_gps_un_vehiculo(
                client, tokens_validos[indice], indice + 1, indice
            )

        inicio = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_vehiculos) as executor:
            futuros = [executor.submit(tarea, i) for i in range(num_vehiculos)]
            for futuro in as_completed(futuros):
                latencia, status, contenido = futuro.result()
                medidor.agregar(latencia, status)
        duracion = time.perf_counter() - inicio

    res = medidor.resumen("telemetria_gps")
    res["duracion_segundos"] = round(duracion, 3)
    res["throughput_rps"] = round(num_vehiculos / duracion, 2) if duracion else 0
    print(f"Total requests: {res['total']}")
    print(f"Exitosos (2xx): {res['exitos']}")
    print(f"Errores: {res['errores']}")
    print(f"Latencia promedio: {res['promedio_ms']} ms")
    print(f"Latencia p95: {res['p95_ms']} ms")
    print(f"Latencia p99: {res['p99_ms']} ms")
    print(f"Duracion total: {res['duracion_segundos']} s")
    print(f"Throughput: {res['throughput_rps']} req/s")
    print(f"Status codes: {res['status_codes']}")
    return res


def ejecutar_prueba_carga_eta(num_pasajeros=100):
    """Ejecuta prueba de carga: N pasajeros consultando ETA simultáneamente."""
    print(f"\n{'='*60}")
    print(f"PRUEBA DE CARGA: {num_pasajeros} pasajeros consultando ETA")
    print(f"{'='*60}")

    medidor = MedidorCarga()

    with httpx.Client(timeout=10.0) as client:
        emails = EMAILS_PASAJEROS[:num_pasajeros]
        tokens = [obtener_token_email(client, email) for email in emails]
        tokens_validos = [t for t in tokens if t]
        if not tokens_validos:
            token = obtener_token(client, "cliente")
            if not token:
                print("ERROR: No se pudo obtener token de cliente")
                return medidor.resumen("eta")
            tokens_validos = [token] * num_pasajeros
        elif len(tokens_validos) < num_pasajeros:
            tokens_validos += [tokens_validos[-1]] * (num_pasajeros - len(tokens_validos))

        def tarea(indice):
            return consultar_eta_un_pasajero(client, tokens_validos[indice], indice)

        inicio = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_pasajeros) as executor:
            futuros = [executor.submit(tarea, i) for i in range(num_pasajeros)]
            for futuro in as_completed(futuros):
                latencia, status, contenido = futuro.result()
                medidor.agregar(latencia, status)
        duracion = time.perf_counter() - inicio

    res = medidor.resumen("eta_pasajeros")
    res["duracion_segundos"] = round(duracion, 3)
    res["throughput_rps"] = round(num_pasajeros / duracion, 2) if duracion else 0
    print(f"Total requests: {res['total']}")
    print(f"Exitosos (2xx): {res['exitos']}")
    print(f"Errores: {res['errores']}")
    print(f"Latencia promedio: {res['promedio_ms']} ms")
    print(f"Latencia p95: {res['p95_ms']} ms")
    print(f"Latencia p99: {res['p99_ms']} ms")
    print(f"Duracion total: {res['duracion_segundos']} s")
    print(f"Throughput: {res['throughput_rps']} req/s")
    print(f"Status codes: {res['status_codes']}")
    return res


def ejecutar_todas_pruebas():
    """Ejecuta todas las pruebas de carga y retorna metricas."""
    resultados = {}

    print("\n" + "="*70)
    print("CONATACOCH Fase 2 - Pruebas de Carga y Rendimiento")
    print(f"Fecha: {datetime.now(timezone.utc).isoformat()}")
    print("="*70)

    resultado_gps = ejecutar_prueba_carga_telemetria(50)
    resultados["telemetria_gps"] = resultado_gps

    resultado_eta = ejecutar_prueba_carga_eta(100)
    resultados["eta_pasajeros"] = resultado_eta

    print("\n" + "="*70)
    print("RESUMEN FINAL DE METRICAS")
    print("="*70)
    for clave, res in resultados.items():
        print(f"\n--- {res['nombre']} ---")
        print(f"  Requests:      {res['total']}")
        print(f"  Exitosos:      {res['exitos']}")
        print(f"  Errores:       {res['errores']}")
        print(f"  Promedio:      {res['promedio_ms']} ms")
        print(f"  p95:           {res['p95_ms']} ms")
        print(f"  p99:           {res['p99_ms']} ms")
        print(f"  Throughput:    {res['throughput_rps']} req/s")

    return resultados


if __name__ == "__main__":
    ejecutar_todas_pruebas()
