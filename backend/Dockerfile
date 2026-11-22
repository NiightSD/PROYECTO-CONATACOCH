# =============================================================================
# CONATACOCH Backend - imagen de produccion
# Base: python:3.12-slim (requerido por la rubrica)
# Driver MySQL: PyMySQL (puro Python) -> sin toolchain nativo en la imagen.
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=conatacoch.settings

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

# Codigo de la aplicacion + dataset semilla inmutable dentro de la imagen.
COPY backend/ /app/
COPY recorridos_conatacoch_taxi_colectivo_2.json /app/data/recorridos_conatacoch_taxi_colectivo_2.json

# Estaticos del admin y de DRF compilados en build (imagen read-only en runtime).
RUN SECRET_KEY=build-only-key \
    MYSQL_PASSWORD=build-only \
    python manage.py collectstatic --noinput \
    && chmod +x /app/entrypoint.sh

# Usuario sin privilegios.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
