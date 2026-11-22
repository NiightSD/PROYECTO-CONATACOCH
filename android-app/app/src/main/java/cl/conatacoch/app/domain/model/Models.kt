package cl.conatacoch.app.domain.model

/** Usuario autenticado en la plataforma. */
data class User(
    val id: Int,
    val rut: String,
    val nombre: String,
    val email: String,
    val rol: String,
) {
    val isDriver: Boolean get() = rol == "CONDUCTOR"
    val isAdmin: Boolean get() = rol == "ADMIN"
    val isPassenger: Boolean get() = rol == "CLIENTE"
    val roleLabel: String
        get() = when (rol) {
            "CONDUCTOR" -> "Conductor"
            "ADMIN" -> "Administrador"
            else -> "Pasajero"
        }
    val initials: String
        get() = nombre.split(" ")
            .filter { it.isNotBlank() }
            .take(2)
            .joinToString("") { it.first().uppercase() }
            .ifBlank { "?" }
}

/** Sesion JWT persistida de forma cifrada. */
data class Session(
    val access: String,
    val refresh: String,
    val user: User,
)

data class Linea(
    val id: Int,
    val folio: Int,
    val nombreRecorrido: String,
    val tipoTrazado: String,
    val comunaOrigen: String,
    val comunaDestino: String,
    val domicilioOrigen: String,
    val domicilioDestino: String,
    val tarifaActual: Double,
) {
    val displayName: String get() = "#$folio · $nombreRecorrido"
}

data class Paradero(
    val id: Int,
    val nombre: String,
    val comuna: String,
    val latitud: Double,
    val longitud: Double,
)

data class EtaOption(
    val conductorId: Int,
    val folio: String,
    val patente: String,
    val distanciaKm: Double,
    val etaMinutos: Double,
    val cupos: Int,
)

data class EtaResult(
    val lineaId: Int,
    val nombreRecorrido: String,
    val nearest: EtaOption?,
    val options: List<EtaOption>,
)

data class FleetVehicle(
    val conductorId: Int,
    val folio: String,
    val patente: String,
    val lineaNombre: String,
    val cupos: Int,
    val latitud: Double,
    val longitud: Double,
    val velocidadKmh: Double,
    val edadSegundos: Int?,
)

data class DriverProfile(
    val id: Int,
    val nombre: String,
    val rut: String,
    val folio: String,
    val patente: String,
    val marcaModelo: String,
    val capacidad: Int,
    val lineaId: Int,
    val lineaFolio: Int,
    val lineaNombre: String,
    val enTurno: Boolean,
    val cupos: Int,
)

data class QrPayment(
    val uuid: String,
    val estado: String,
    val monto: Double,
    val conductorFolio: String,
    val lineaFolio: Int,
)

data class Transaction(
    val id: Int,
    val uuid: String,
    val monto: Double,
    val estado: String,
    val estadoDisplay: String,
    val pasajeroRut: String,
    val conductorFolio: String,
    val lineaFolio: Int,
    val fechaHora: String,
)

data class TelemetryAck(
    val velocidadCalculada: Double,
    val alertaSpoofing: Boolean,
)

data class TurnoOtp(
    val codigo: String?,
    val expiraMinutos: Int,
    val detail: String,
)
