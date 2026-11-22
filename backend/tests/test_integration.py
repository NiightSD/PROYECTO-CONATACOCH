"""
Pruebas de integracion Fase 2:
  * Login y obtencion de JWT.
  * Registro de conductor por ADMIN.
  * Inicio de turno con OTP y sesion unica.
  * Flujo de pago QR (cliente genera, conductor confirma).
  * Cambio de cupos.
"""
from __future__ import annotations

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

import pytest

from core.models import Usuario, Conductor, TransaccionPago

pytestmark = pytest.mark.django_db


class TestLoginIntegracion:
    def test_login_devuelve_access_y_refresh(self, api_client, cliente_user):
        url = reverse("auth-login")
        resp = api_client.post(
            url,
            {"email": cliente_user.email, "password": "PasajeroPass123!"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert data["usuario"]["email"] == cliente_user.email
        assert data["usuario"]["rol"] == "CLIENTE"

    def test_login_password_incorrecto_401(self, api_client, cliente_user):
        url = reverse("auth-login")
        resp = api_client.post(
            url,
            {"email": cliente_user.email, "password": "wrongpassword"},
            format="json",
        )
        assert resp.status_code == 401

    def test_login_usuario_inexistente_401(self, api_client):
        url = reverse("auth-login")
        resp = api_client.post(
            url,
            {"email": "noexiste@test.cl", "password": "cualquiera123"},
            format="json",
        )
        assert resp.status_code == 401


class TestRegistroConductorAdmin:
    def test_admin_registra_conductor_exitoso(
        self, auth_client_admin, admin_user, linea_colectiva, vehiculo
    ):
        # Crear usuario conductor primero
        usuario_conductor = Usuario.objects.create_user(
            email="nuevo.conductor@test.cl",
            rut="22.222.222-2",
            nombre="Nuevo Conductor",
            password="ConducPass123!",
            rol="CONDUCTOR",
        )

        url = reverse("admin-conductor-registro")
        resp = auth_client_admin.post(
            url,
            {
                "usuario_id": usuario_conductor.id,
                "folio_conatacoch": "999001",
                "patente": "XYZ-34",
                "cupos_disponibles": 4,
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        data = resp.json()
        assert data["folio_conatacoch"] == "999001"
        assert data["patente"] == "XYZ-34"
        assert data["cupos_disponibles"] == 4

    def test_cliente_no_puede_registrar_conductor_403(
        self, auth_client_cliente, cliente_user
    ):
        url = reverse("admin-conductor-registro")
        resp = auth_client_cliente.post(
            url,
            {
                "usuario_id": cliente_user.id,
                "folio_conatacoch": "999002",
                "patente": "ABC-12",
            },
            format="json",
        )
        assert resp.status_code == 403

    def test_admin_listado_conductores_paginado(
        self, auth_client_admin, conductor, conductor_user
    ):
        url = reverse("admin-conductores-list")
        resp = auth_client_admin.get(url)
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert "results" in data
        assert data["count"] >= 1


class TestInicioTurnoConductor:
    def test_iniciar_turno_solicita_otp(self, auth_client_conductor, conductor):
        url = reverse("conductor-iniciar-turno")
        resp = auth_client_conductor.post(
            url, {"solicitar_codigo": True}, format="json"
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data["estado"] == "otp_requerido"
        assert "codigo_otp" in data

    def test_iniciar_turno_con_otp_valido(self, auth_client_conductor, conductor):
        # Primero solicitar OTP
        url = reverse("conductor-iniciar-turno")
        resp_solicitud = auth_client_conductor.post(
            url, {"solicitar_codigo": True}, format="json"
        )
        codigo = resp_solicitud.json()["codigo_otp"]

        # Luego validar OTP
        resp = auth_client_conductor.post(
            url, {"codigo_otp": codigo}, format="json"
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data["estado"] == "turno_iniciado"
        assert data["en_turno"] is True
        assert "token_sesion" in data

        # Verificar en DB
        conductor.refresh_from_db()
        assert conductor.en_turno is True
        assert conductor.token_sesion_activa != ""

    def test_iniciar_turno_otp_invalido_401(self, auth_client_conductor, conductor):
        # Preparar un OTP vigente y enviar uno distinto
        conductor.otp_codigo = "123456"
        conductor.otp_codigo_expira = timezone.now() + timedelta(minutes=5)
        conductor.save(update_fields=["otp_codigo", "otp_codigo_expira"])

        url = reverse("conductor-iniciar-turno")
        resp = auth_client_conductor.post(
            url, {"codigo_otp": "000000"}, format="json"
        )
        assert resp.status_code == 401

    def test_sesion_unica_invalida_token_previo(
        self, auth_client_conductor, conductor
    ):
        # Simular token de sesion previo
        conductor.token_sesion_activa = "hash_sesion_previa"
        conductor.en_turno = True
        conductor.save(update_fields=["token_sesion_activa", "en_turno"])

        # Solicitar nuevo OTP
        url = reverse("conductor-iniciar-turno")
        resp_solicitud = auth_client_conductor.post(
            url, {"solicitar_codigo": True}, format="json"
        )
        codigo = resp_solicitud.json()["codigo_otp"]

        # Iniciar turno de nuevo - debe invalidar sesion previa
        resp = auth_client_conductor.post(
            url, {"codigo_otp": codigo}, format="json"
        )
        assert resp.status_code == 200

        conductor.refresh_from_db()
        assert conductor.token_sesion_activa != "hash_sesion_previa"


class TestCambioCuposConductor:
    def test_conductor_cambia_cupos_exitoso(
        self, auth_client_conductor, conductor
    ):
        # Iniciar turno primero
        url_turno = reverse("conductor-iniciar-turno")
        auth_client_conductor.post(
            url_turno, {"solicitar_codigo": True}, format="json"
        )
        resp_solicitud = auth_client_conductor.post(
            url_turno, {"solicitar_codigo": True}, format="json"
        )
        # Obtener codigo de la respuesta anterior (en test real vendria por SMS)
        # Para este test, forzar en_turno
        conductor.en_turno = True
        conductor.save(update_fields=["en_turno"])

        url = reverse("conductor-cupos")
        resp = auth_client_conductor.post(
            url, {"cupos_disponibles": 3}, format="json"
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data["cupos_disponibles"] == 3

        conductor.refresh_from_db()
        assert conductor.cupos_disponibles == 3

    def test_conductor_sin_turno_no_puede_cambiar_cupos_403(
        self, auth_client_conductor, conductor
    ):
        url = reverse("conductor-cupos")
        resp = auth_client_conductor.post(
            url, {"cupos_disponibles": 3}, format="json"
        )
        assert resp.status_code == 403


class TestFlujoPagoQR:
    def test_cliente_genera_qr_y_conductor_confirma(
        self, auth_client_cliente, auth_client_conductor, conductor, linea_colectiva
    ):
        # Conductor debe estar en turno
        conductor.en_turno = True
        conductor.save(update_fields=["en_turno"])

        # Cliente genera QR
        url_qr = reverse("pago-qr")
        resp_qr = auth_client_cliente.post(
            url_qr,
            {
                "conductor_id": conductor.id,
                "linea_id": linea_colectiva.id,
                "monto": 1000.00,
            },
            format="json",
        )
        assert resp_qr.status_code == 201, resp_qr.content
        qr_data = resp_qr.json()
        codigo_qr = qr_data["codigo_qr_uuid"]
        assert qr_data["estado"] == "PENDIENTE"

        # Conductor confirma pago
        url_confirmar = reverse("pago-confirmar")
        resp_conf = auth_client_conductor.post(
            url_confirmar,
            {"codigo_qr_uuid": codigo_qr},
            format="json",
        )
        assert resp_conf.status_code == 200, resp_conf.content
        conf_data = resp_conf.json()
        assert conf_data["estado"] == "PAGADO"
        assert conf_data["monto"] == "1000.00"

        # Verificar en DB
        transaccion = TransaccionPago.objects.get(codigo_qr_uuid=codigo_qr)
        assert transaccion.estado == TransaccionPago.Estado.PAGADO

    def test_cliente_no_puede_confirmar_pago_ajeno_403(
        self, auth_client_cliente, cliente_user, conductor, linea_colectiva
    ):
        # Crear transaccion pendiente directamente
        transaccion = TransaccionPago.objects.create(
            pasajero=cliente_user,
            conductor=conductor,
            linea=linea_colectiva,
            monto=500.00,
            estado=TransaccionPago.Estado.PENDIENTE,
        )

        # Otro cliente intenta confirmar (debe fallar - no es conductor)
        url_confirmar = reverse("pago-confirmar")
        resp = auth_client_cliente.post(
            url_confirmar,
            {"codigo_qr_uuid": str(transaccion.codigo_qr_uuid)},
            format="json",
        )
        assert resp.status_code == 403

    def test_conductor_confirma_pago_de_otro_conductor_403(
        self, auth_client_conductor, cliente_user, conductor, linea_colectiva, admin_user
    ):
        # Crear otro conductor
        otro_usuario = Usuario.objects.create_user(
            email="otro.conductor@test.cl",
            rut="33.333.333-3",
            nombre="Otro Conductor",
            password="ConducPass123!",
            rol="CONDUCTOR",
        )
        from core.models import Vehiculo
        otro_vehiculo = Vehiculo.objects.create(
            patente="EFGH-34",
            marca_modelo="Hyundai",
            capacidad_pasajeros=4,
            linea=linea_colectiva,
        )
        otro_conductor = Conductor.objects.create(
            usuario=otro_usuario,
            folio_conatacoch="236001",
            vehiculo=otro_vehiculo,
            en_turno=True,
            cupos_disponibles=2,
        )

        # Crear transaccion del otro conductor
        transaccion = TransaccionPago.objects.create(
            pasajero=cliente_user,
            conductor=otro_conductor,
            linea=linea_colectiva,
            monto=800.00,
            estado=TransaccionPago.Estado.PENDIENTE,
        )

        # Conductor autenticado intenta confirmar pago de otro conductor (IDOR)
        url_confirmar = reverse("pago-confirmar")
        resp = auth_client_conductor.post(
            url_confirmar,
            {"codigo_qr_uuid": str(transaccion.codigo_qr_uuid)},
            format="json",
        )
        assert resp.status_code == 403, resp.content
