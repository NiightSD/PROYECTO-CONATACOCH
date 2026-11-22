package cl.conatacoch.app.data.repository

import cl.conatacoch.app.core.safeApiCall
import cl.conatacoch.app.data.remote.ApiService
import cl.conatacoch.app.data.remote.dto.CuposRequestDto
import cl.conatacoch.app.data.remote.dto.PagoConfirmarRequestDto
import cl.conatacoch.app.data.remote.dto.TelemetriaRequestDto
import cl.conatacoch.app.data.remote.dto.TurnoRequestDto
import cl.conatacoch.app.data.remote.dto.toDomain
import cl.conatacoch.app.data.remote.dto.toOtp
import cl.conatacoch.app.domain.model.DriverProfile
import cl.conatacoch.app.domain.model.TelemetryAck
import cl.conatacoch.app.domain.model.Transaction
import cl.conatacoch.app.domain.model.TurnoOtp
import cl.conatacoch.app.domain.repository.DriverRepository
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class DriverRepositoryImpl(
    private val api: ApiService,
) : DriverRepository {

    override suspend fun perfil(): Result<DriverProfile> = safeApiCall {
        api.perfilConductor().toDomain()
    }

    override suspend fun solicitarOtp(finalizar: Boolean): Result<TurnoOtp> = safeApiCall {
        val response = if (finalizar) {
            api.finalizarTurno(TurnoRequestDto(solicitarCodigo = true))
        } else {
            api.iniciarTurno(TurnoRequestDto(solicitarCodigo = true))
        }
        response.toOtp()
    }

    override suspend fun confirmarTurno(codigo: String, finalizar: Boolean): Result<Unit> =
        safeApiCall {
            if (finalizar) {
                api.finalizarTurno(TurnoRequestDto(codigoOtp = codigo))
            } else {
                api.iniciarTurno(TurnoRequestDto(codigoOtp = codigo))
            }
            Unit
        }

    override suspend fun actualizarCupos(cupos: Int): Result<Int> = safeApiCall {
        api.actualizarCupos(CuposRequestDto(cupos)).cuposDisponibles ?: cupos
    }

    override suspend fun enviarTelemetria(
        latitud: Double,
        longitud: Double,
        velocidadKmh: Double,
        rumbo: Double,
        cupos: Int,
    ): Result<TelemetryAck> = safeApiCall {
        api.enviarTelemetria(
            TelemetriaRequestDto(
                latitud = latitud,
                longitud = longitud,
                velocidadKmh = velocidadKmh,
                rumbo = rumbo,
                cuposDisponibles = cupos,
                timestamp = isoNow(),
            )
        ).toDomain()
    }

    override suspend fun pagosPendientes(conductorId: Int): Result<List<Transaction>> =
        safeApiCall {
            api.transacciones(
                estado = "PENDIENTE",
                conductorId = conductorId,
                pageSize = 20,
            ).results.orEmpty().map { it.toDomain() }
        }

    override suspend fun confirmarPago(uuid: String): Result<Unit> = safeApiCall {
        api.confirmarPago(PagoConfirmarRequestDto(uuid))
        Unit
    }

    private fun isoNow(): String {
        val formatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)
        formatter.timeZone = TimeZone.getTimeZone("UTC")
        return formatter.format(Date())
    }
}
