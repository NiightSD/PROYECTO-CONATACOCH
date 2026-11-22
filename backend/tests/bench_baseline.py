"""Benchmark secuencial (linea base) para separar latencia propia del servidor
del efecto de contencion concurrente.

Uso:
    BASE_URL=http://127.0.0.1:8001 python tests/bench_baseline.py
"""
from __future__ import annotations

import os
import statistics
import time

import httpx

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8001")
PASSWORD = "CargaPass123!"


def pct(valores, p):
    ordenados = sorted(valores)
    idx = int(p * len(ordenados)) - 1
    return ordenados[max(idx, 0)]


def login(client, email):
    r = client.post(
        f"{BASE_URL}/api/auth/login/",
        json={"email": email, "password": PASSWORD},
        timeout=15.0,
    )
    r.raise_for_status()
    return r.json()["access"]


def main():
    with httpx.Client(timeout=20.0) as client:
        # tokens
        token_c = login(client, "carga01@test.cl")
        token_p = login(client, "pasajero001@test.cl")

        h_c = {"Authorization": f"Bearer {token_c}"}
        h_p = {"Authorization": f"Bearer {token_p}"}

        # --- Telemetria secuencial (20 envios) ---
        lat_t = []
        for i in range(20):
            body = {
                "latitud": -33.45 + i * 0.0001,
                "longitud": -70.66 + i * 0.0001,
                "velocidad_kmh": 28.0,
                "rumbo": 90.0,
                "cupos_disponibles": 3,
            }
            t0 = time.perf_counter()
            r = client.post(f"{BASE_URL}/api/telemetria/enviar/", json=body, headers=h_c)
            lat_t.append((time.perf_counter() - t0) * 1000)
            assert r.status_code == 201, (r.status_code, r.text)

        # --- ETA secuencial (20 consultas) ---
        lat_e = []
        for i in range(20):
            body = {
                "linea_id": 1,
                "latitud_pasajero": -33.44 + i * 0.0001,
                "longitud_pasajero": -70.65,
            }
            t0 = time.perf_counter()
            r = client.post(f"{BASE_URL}/api/eta/calcular/", json=body, headers=h_p)
            lat_e.append((time.perf_counter() - t0) * 1000)
            assert r.status_code == 200, (r.status_code, r.text)

        for nombre, lat in (("telemetria", lat_t), ("eta", lat_e)):
            print(
                f"{nombre}: n={len(lat)} avg={statistics.mean(lat):.1f}ms "
                f"p50={pct(lat, 0.5):.1f}ms p95={pct(lat, 0.95):.1f}ms "
                f"min={min(lat):.1f}ms max={max(lat):.1f}ms"
            )


if __name__ == "__main__":
    main()
