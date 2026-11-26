
from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_env_local() -> None:
    """Carga `.env` (raiz del repo o backend) sin pisar variables exportadas.

    En Docker las variables llegan por `environment:`; en local este loader
    permite que `manage.py` use exactamente MYSQL_*, MONGO_* y JWT_* del .env.
    Las variables ya presentes en el proceso siempre tienen prioridad (12-factor).
    """
    for ruta in (BASE_DIR.parent / ".env", BASE_DIR / ".env"):
        if not ruta.is_file():
            continue
        try:
            contenido = ruta.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        for linea in contenido.splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            if not clave or clave in os.environ:
                continue
            os.environ[clave] = valor.strip().strip('"').strip("'")


_cargar_env_local()

# pytest siempre corre con SQLite salvo que se fuerce DB_ENGINE explicitamente.
RUNNING_PYTEST = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ


# -----------------------------------------------------------------------------
# Helpers de entorno
# -----------------------------------------------------------------------------
def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "si", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(env(name, str(default)))
    except ValueError:
        return default


def env_list(name: str, default: str = "") -> list[str]:
    raw = env(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# -----------------------------------------------------------------------------
# Noyau / seguridad
# -----------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", False)
SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-secret-key-change-me")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,backend,web_admin")

if DEBUG:
    for _dev_host in ("10.0.2.2", "0.0.0.0", "host.docker.internal"):
        if _dev_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_dev_host)

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
)
if DEBUG:
    for _dev_origin in (
        "http://10.0.2.2:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ):
        if _dev_origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_dev_origin)

# CORS solo se aplica con DEBUG=True (panel servido en :8080 o :8000).
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://localhost:8000,http://127.0.0.1:8000",
)

# Nginx termina TLS y propaga X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Tras el login del admin, volver al panel (evita el /accounts/profile/ por defecto).
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/admin/login/"

# En produccion con HTTPS, activar por entorno.
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)

# Limites de entrada
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024


# -----------------------------------------------------------------------------
# Aplicaciones
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.DevCorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "conatacoch.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "conatacoch.wsgi.application"
ASGI_APPLICATION = "conatacoch.asgi.application"

AUTH_USER_MODEL = "core.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# -----------------------------------------------------------------------------
# Base de datos relacional (MySQL 8 + pool de conexiones)
# -----------------------------------------------------------------------------
DB_ENGINE = env(
    "DB_ENGINE",
    "django.db.backends.sqlite3" if RUNNING_PYTEST else "django.db.backends.mysql",
)
DB_WAIT_RETRIES = env_int("DB_WAIT_RETRIES", 30)
DB_WAIT_DELAY = env_int("DB_WAIT_DELAY", 2)

# Backend propio: hereda el oficial de MySQL y relaja el minimo de MariaDB
# (Django 5.2 pide 10.5; el entorno academico local usa 10.4, compatible).
DB_BACKEND = (
    "core.db_backend" if DB_ENGINE.endswith(("mysql", "mariadb")) else DB_ENGINE
)

if DB_ENGINE.endswith("sqlite3"):
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": env("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
            "OPTIONS": {"timeout": env_int("SQLITE_TIMEOUT", 30)},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_BACKEND,
            "NAME": env("MYSQL_DATABASE", "conatacoch"),
            "USER": env("MYSQL_USER", "conatacoch"),
            "PASSWORD": env("MYSQL_PASSWORD", "conatacoch_2026"),
            "HOST": env("MYSQL_HOST", "db_mysql"),
            "PORT": env("MYSQL_PORT", "3306"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 600),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": (
                    "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,"
                    "NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO'"
                ),
                "connect_timeout": 10,
            },
        }
    }


# -----------------------------------------------------------------------------
# Cache / sesiones
# -----------------------------------------------------------------------------
SESSION_ENGINE = "django.contrib.sessions.backends.db"



# Hashing de passwords - Argon2id

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]


# -----------------------------------------------------------------------------
# Django REST Framework + JWT + OpenAPI
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", "60/min"),
        "user": env("THROTTLE_USER", "600/min"),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}

JWT_SECRET = env("JWT_SECRET") or SECRET_KEY

# Clave dedicada para cifrar secretos TOTP 
OTP_ENCRYPTION_KEY = env("OTP_ENCRYPTION_KEY")

SIMPLE_JWT = {
    "SIGNING_KEY": JWT_SECRET,
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("ACCESS_TOKEN_MINUTES", 15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("REFRESH_TOKEN_DAYS", 7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "UPDATE_LAST_LOGIN": True,
}


# -----------------------------------------------------------------------------
# Manejo global de excepciones
# -----------------------------------------------------------------------------
EXCEPTION_HANDLER = "core.security.custom_exception_handler"

REST_FRAMEWORK["EXCEPTION_HANDLER"] = EXCEPTION_HANDLER

SPECTACULAR_SETTINGS = {
    "TITLE": "CONATACOCH API",
    "DESCRIPTION": (
        "API de la plataforma de Taxis y Colectivos de Chile (CONATACOCH).\n\n"
        "**Fase 1**: infraestructura, modelo relacional 3FN, carga inicial y "
        "telemetria geoespacial en MongoDB Atlas.\n\n"
        "Autenticacion: `POST /api/token/` (JWT) y luego "
        "`Authorization: Bearer <access>`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
    },
    "REDOC_DIST": "SIDECAR",
    "TAGS": [
        {"name": "Salud", "description": "Liveness / readiness del servicio."},
        {"name": "Lineas", "description": "Recorridos de taxi colectivo (RM)."},
        {"name": "Paraderos", "description": "Paraderos base georreferenciados."},
        {"name": "Flota", "description": "Vehiculos y conductores."},
        {"name": "Pagos", "description": "Transacciones QR del sistema."},
    ],
}


# -----------------------------------------------------------------------------
# MongoDB Atlas / fallback local
# -----------------------------------------------------------------------------
MONGO_ATLAS_URI = env("MONGO_ATLAS_URI")
MONGO_LOCAL_URI = env("MONGO_LOCAL_URI", "mongodb://mongo_local:27017")

MONGO_URI = MONGO_ATLAS_URI or MONGO_LOCAL_URI
MONGO_USE_TLS = bool(MONGO_ATLAS_URI) or env_bool("MONGO_TLS", False)
MONGO_DB_NAME = env("MONGO_DB_NAME", "telemetria_ubicacion")
MONGO_COLLECTION = env("MONGO_COLLECTION", "ubicaciones")
MONGO_TTL_SECONDS = env_int("MONGO_TTL_SECONDS", 14400) 
MONGO_MAX_POOL_SIZE = env_int("MONGO_MAX_POOL_SIZE", 50)
MONGO_MIN_POOL_SIZE = env_int("MONGO_MIN_POOL_SIZE", 5)
MONGO_TIMEOUT_MS = env_int("MONGO_TIMEOUT_MS", 5000)
# Solo para pruebas de carga locales sin servidor MongoDB real.
# pytest usa mongomock automaticamente (ver tests/conftest.py).
MONGO_MOCK = env_bool("MONGO_MOCK", RUNNING_PYTEST)


# -----------------------------------------------------------------------------
# Internacionalizacion
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------------
# Archivos estaticos
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {

        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0
WHITENOISE_USE_FINDERS = DEBUG

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

APPEND_SLASH = True


# -----------------------------------------------------------------------------
# Logging a stdout
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {process:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "core": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO"),
                 "propagate": False},
        "pymongo": {"handlers": ["console"], "level": "WARNING",
                    "propagate": False},
    },
}


# -----------------------------------------------------------------------------
# Base de datos de pruebas (pytest) - usa SQLite en memoria por defecto
# -----------------------------------------------------------------------------
TEST_DB_ENGINE = env("TEST_DB_ENGINE", "django.db.backends.sqlite3")
if TEST_DB_ENGINE.endswith("sqlite3"):
    DATABASES["default"]["TEST"] = {
        "ENGINE": TEST_DB_ENGINE,
        "NAME": ":memory:",
    }



# Umbral de velocidad para deteccion de GPS spoofing (km/h)
VELOCIDAD_MAXIMA_KMH = env_int("VELOCIDAD_MAXIMA_KMH", 130)

# Intentos fallidos antes de bloqueo y minutos de bloqueo
MAX_INTENTOS_FALLIDOS = env_int("MAX_INTENTOS_FALLIDOS", 5)
MINUTOS_BLOQUEO = env_int("MINUTOS_BLOQUEO", 15)

# Tiempo de expiracion de codigo OTP (minutos)
OTP_EXPIRACION_MINUTOS = env_int("OTP_EXPIRACION_MINUTOS", 5)
