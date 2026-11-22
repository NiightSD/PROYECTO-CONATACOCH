"""
Configuracion de pytest para CONATACOCH Fase 2.

Fixtures globales para pruebas de integracion, seguridad y carga.
pytest-django crea una base de datos de prueba aislada y hace rollback
de cada test, por lo que no se requiere un django_db_setup manual.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def mongomock_collection(monkeypatch):
    """Reemplaza la coleccion MongoDB por mongomock (en memoria)."""
    import mongomock
    from core import mongo

    cliente = mongomock.MongoClient()
    db = cliente["telemetria_ubicacion"]
    coleccion = db["ubicaciones"]

    monkeypatch.setattr(mongo, "get_collection", lambda: coleccion)
    monkeypatch.setattr(mongo, "get_database", lambda: db)
    return coleccion


@pytest.fixture
def admin_user(django_user_model):
    """Crea un usuario ADMIN para pruebas."""
    return django_user_model.objects.create_superuser(
        email="admin@test.cl",
        rut="11.111.111-1",
        nombre="Admin Test",
        password="AdminPass123!",
    )


@pytest.fixture
def conductor_user(django_user_model):
    """Crea un usuario CONDUCTOR para pruebas."""
    return django_user_model.objects.create_user(
        email="conductor@test.cl",
        rut="22.222.222-2",
        nombre="Conductor Test",
        password="ConducPass123!",
        rol="CONDUCTOR",
    )


@pytest.fixture
def cliente_user(django_user_model):
    """Crea un usuario CLIENTE para pruebas."""
    return django_user_model.objects.create_user(
        email="cliente@test.cl",
        rut="44.444.444-4",
        nombre="Cliente Test",
        password="PasajeroPass123!",
        rol="CLIENTE",
    )


@pytest.fixture
def linea_colectiva():
    """Crea una linea colectiva de prueba."""
    from core.models import LineaColectiva
    return LineaColectiva.objects.create(
        region=13,
        folio=234001,
        tipo_servicio="AUTOMOVIL URBANO TAXI COLECTIVO",
        nombre_recorrido="Recorrido Test",
        tipo_trazado="PRINCIPAL",
        nombre_origen="Origen Test",
        comuna_origen="Santiago",
        domicilio_origen="Direccion Origen",
        nombre_destino="Destino Test",
        comuna_destino="Providencia",
        domicilio_destino="Direccion Destino",
        tarifa_actual=1000.00,
    )


@pytest.fixture
def vehiculo(linea_colectiva):
    """Crea un vehiculo de prueba."""
    from core.models import Vehiculo
    return Vehiculo.objects.create(
        patente="ABCD-12",
        marca_modelo="Toyota Corolla",
        capacidad_pasajeros=4,
        linea=linea_colectiva,
    )


@pytest.fixture
def conductor(conductor_user, vehiculo):
    """Crea un perfil de conductor para pruebas."""
    from core.models import Conductor
    return Conductor.objects.create(
        usuario=conductor_user,
        folio_conatacoch="234001",
        vehiculo=vehiculo,
        en_turno=False,
        cupos_disponibles=0,
    )


@pytest.fixture
def api_client():
    """Cliente de API de Django REST Framework."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def auth_client_conductor(conductor_user):
    """Cliente autenticado como conductor (instancia independiente)."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(conductor_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def auth_client_admin(admin_user):
    """Cliente autenticado como admin (instancia independiente)."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def auth_client_cliente(cliente_user):
    """Cliente autenticado como cliente (instancia independiente)."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(cliente_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client
