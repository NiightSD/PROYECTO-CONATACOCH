package cl.conatacoch.app.data.repository

import cl.conatacoch.app.core.safeApiCall
import cl.conatacoch.app.data.remote.ApiService
import cl.conatacoch.app.data.remote.dto.EtaRequestDto
import cl.conatacoch.app.data.remote.dto.PagoQrRequestDto
import cl.conatacoch.app.data.remote.dto.toDomain
import cl.conatacoch.app.domain.model.EtaResult
import cl.conatacoch.app.domain.model.FleetVehicle
import cl.conatacoch.app.domain.model.Linea
import cl.conatacoch.app.domain.model.Paradero
import cl.conatacoch.app.domain.model.QrPayment
import cl.conatacoch.app.domain.model.Transaction
import cl.conatacoch.app.domain.repository.PassengerRepository
import java.util.Locale

class PassengerRepositoryImpl(
    private val api: ApiService,
) : PassengerRepository {

    override suspend fun buscarLineas(query: String): Result<List<Linea>> = safeApiCall {
        api.lineas(search = query.ifBlank { null }, pageSize = 20)
            .results
            .orEmpty()
            .map { it.toDomain() }
            .filter { it.id > 0 }
    }

    override suspend fun paraderos(lineaId: Int): Result<List<Paradero>> = safeApiCall {
        api.paraderos(lineaId = lineaId)
            .results
            .orEmpty()
            .mapNotNull { it.toDomain() }
    }

    override suspend fun flota(lineaId: Int): Result<List<FleetVehicle>> = safeApiCall {
        api.flota(lineaId = lineaId)
            .vehiculos
            .orEmpty()
            .mapNotNull { it.toDomain() }
    }

    override suspend fun eta(
        lineaId: Int,
        latitud: Double,
        longitud: Double,
    ): Result<EtaResult> = safeApiCall {
        api.calcularEta(
            EtaRequestDto(
                lineaId = lineaId,
                latitudPasajero = latitud,
                longitudPasajero = longitud,
            )
        ).toDomain()
    }

    override suspend fun crearPago(
        conductorId: Int,
        lineaId: Int,
        monto: Double,
    ): Result<QrPayment> = safeApiCall {
        api.crearPagoQr(
            PagoQrRequestDto(
                conductorId = conductorId,
                lineaId = lineaId,
                monto = String.format(Locale.US, "%.2f", monto),
            )
        ).toDomain()
    }

    override suspend fun buscarTransaccion(uuid: String): Result<Transaction?> = safeApiCall {
        api.transacciones(search = uuid, pageSize = 5)
            .results
            .orEmpty()
            .firstOrNull { it.codigoQrUuid == uuid }
            ?.toDomain()
    }
}
