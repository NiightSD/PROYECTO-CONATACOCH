package cl.conatacoch.app.domain.repository

import cl.conatacoch.app.domain.model.DriverProfile
import cl.conatacoch.app.domain.model.EtaResult
import cl.conatacoch.app.domain.model.FleetVehicle
import cl.conatacoch.app.domain.model.Linea
import cl.conatacoch.app.domain.model.Paradero
import cl.conatacoch.app.domain.model.QrPayment
import cl.conatacoch.app.domain.model.Session
import cl.conatacoch.app.domain.model.TelemetryAck
import cl.conatacoch.app.domain.model.Transaction
import cl.conatacoch.app.domain.model.TurnoOtp
import kotlinx.coroutines.flow.StateFlow

interface AuthRepository {
    fun session(): StateFlow<Session?>
    suspend fun login(email: String, password: String): Result<Session>
    fun logout()
}

interface PassengerRepository {
    suspend fun buscarLineas(query: String): Result<List<Linea>>
    suspend fun paraderos(lineaId: Int): Result<List<Paradero>>
    suspend fun flota(lineaId: Int): Result<List<FleetVehicle>>
    suspend fun eta(lineaId: Int, latitud: Double, longitud: Double): Result<EtaResult>
    suspend fun crearPago(conductorId: Int, lineaId: Int, monto: Double): Result<QrPayment>
    suspend fun buscarTransaccion(uuid: String): Result<Transaction?>
}

interface DriverRepository {
    suspend fun perfil(): Result<DriverProfile>
    suspend fun solicitarOtp(finalizar: Boolean): Result<TurnoOtp>
    suspend fun confirmarTurno(codigo: String, finalizar: Boolean): Result<Unit>
    suspend fun actualizarCupos(cupos: Int): Result<Int>
    suspend fun enviarTelemetria(
        latitud: Double,
        longitud: Double,
        velocidadKmh: Double,
        rumbo: Double,
        cupos: Int,
    ): Result<TelemetryAck>
    suspend fun pagosPendientes(conductorId: Int): Result<List<Transaction>>
    suspend fun confirmarPago(uuid: String): Result<Unit>
}
