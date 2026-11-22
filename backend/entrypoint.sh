#!/bin/sh
# =============================================================================
# CONATACOCH - entrypoint idempotente y stateless
# Orden: espera MySQL -> migra -> seed -> indices Mongo -> gunicorn
# =============================================================================
set -eu

cd /app

echo "[entrypoint] Iniciando CONATACOCH backend..."
echo "[entrypoint] Django settings: ${DJANGO_SETTINGS_MODULE:-conatacoch.settings}"

# 1) Espera activa a MySQL (healthcheck de compose + defensa en profundidad).
python manage.py wait_for_db

# 2) Esquema relacional (idempotente).
python manage.py migrate --noinput

# 3) Carga inicial idempotente del dataset y usuarios demo.
if [ "${SEED_ON_START:-true}" = "true" ]; then
    python manage.py seed_conatacoch
else
    echo "[entrypoint] SEED_ON_START=false: se omite la carga inicial."
fi

# 4) Indices MongoDB (2dsphere, compuesto y TTL). No bloquea el arranque:
#    en Fase 1 Atlas puede no estar aprovisionado todavia.
if ! python manage.py init_mongo_indexes; then
    echo "[entrypoint] ADVERTENCIA: no fue posible crear indices MongoDB." >&2
    echo "[entrypoint] Configure MONGO_ATLAS_URI o use el perfil mongo-local." >&2
fi

# 5) Servidor de aplicaciones. Gunicorn con workers/threads => pool de conexiones.
exec gunicorn conatacoch.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --worker-class gthread \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
