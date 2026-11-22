package cl.conatacoch.app.data.remote.dto

import com.google.gson.annotations.SerializedName

/**
 * DTOs espejo de la API real de CONATACOCH.
 *
 * Los campos se declaran nullable a proposito: Gson instancia los objetos sin
 * invocar el constructor de Kotlin, por lo que un campo ausente quedaria en
 * null aunque el tipo sea no-null. Los mappers convierten con valores por
 * defecto seguros.
 */

data class PaginatedDto<T>(
    val count: Int? = null,
    val next: String? = null,
    val previous: String? = null,
    val results: List<T>? = null,
)

// ------------------------------------------------------------------ Auth
data class UsuarioDto(
    val id: Int? = null,
    val rut: String? = null,
    val nombre: String? = null,
    val email: String? = null,
    val rol: String? = null,
)

data class LoginRequestDto(val email: String, val password: String)
data class RefreshRequestDto(val refresh: String)

data class LoginResponseDto(
    val access: String? = null,
    val refresh: String? = null,
    val usuario: UsuarioDto? = null,
)

data class RefreshResponseDto(val access: String? = null)

// --------------------------------------------------------------- Catalogos
data class LineaDto(
    val id: Int? = null,
    val region: Int? = null,
    val folio: Int? = null,
    @SerializedName("tipo_servicio") val tipoServicio: String? = null,
    @SerializedName("nombre_recorrido") val nombreRecorrido: String? = null,
    @SerializedName("tipo_trazado") val tipoTrazado: String? = null,
    @SerializedName("nombre_origen") val nombreOrigen: String? = null,
    @SerializedName("comuna_origen") val comunaOrigen: String? = null,
    @SerializedName("domicilio_origen") val domicilioOrigen: String? = null,
    @SerializedName("nombre_destino") val nombreDestino: String? = null,
    @SerializedName("comuna_destino") val comunaDestino: String? = null,
    @SerializedName("domicilio_destino") val domicilioDestino: String? = null,
    @SerializedName("tarifa_actual") val tarifaActual: String? = null,
)

data class ParaderoDto(
    val id: Int? = null,
    val nombre: String? = null,
    val comuna: String? = null,
    val latitud: String? = null,
    val longitud: String? = null,
    val linea: Int? = null,
)

// -------------------------------------------------------------------- ETA
data class EtaRequestDto(
    @SerializedName("linea_id") val lineaId: Int,
    @SerializedName("latitud_pasajero") val latitudPasajero: Double,
    @SerializedName("longitud_pasajero") val longitudPasajero: Double,
)

data class EtaOptionDto(
    @SerializedName("conductor_id") val conductorId: Int? = null,
    @SerializedName("folio_conatacoch") val folioConatacoch: String? = null,
    val patente: String? = null,
    @SerializedName("distancia_km") val distanciaKm: Double? = null,
    @SerializedName("eta_segundos") val etaSegundos: Int? = null,
    @SerializedName("eta_minutos") val etaMinutos: Double? = null,
    @SerializedName("cupos_disponibles") val cuposDisponibles: Int? = null,
    @SerializedName("ultima_actualizacion") val ultimaActualizacion: String? = null,
)

data class EtaResponseDto(
    @SerializedName("linea_id") val lineaId: Int? = null,
    @SerializedName("nombre_recorrido") val nombreRecorrido: String? = null,
    @SerializedName("conductor_mas_cercano") val conductorMasCercano: EtaOptionDto? = null,
    val opciones: List<EtaOptionDto>? = null,
)

// ------------------------------------------------------------------ Flota
data class FleetVehicleDto(
    @SerializedName("conductor_id") val conductorId: Int? = null,
    @SerializedName("id_vehiculo") val idVehiculo: Int? = null,
    @SerializedName("folio_conatacoch") val folioConatacoch: String? = null,
    @SerializedName("usuario_nombre") val usuarioNombre: String? = null,
    val patente: String? = null,
    @SerializedName("linea_id") val lineaId: Int? = null,
    @SerializedName("linea_folio") val lineaFolio: Int? = null,
    @SerializedName("linea_nombre") val lineaNombre: String? = null,
    @SerializedName("cupos_disponibles") val cuposDisponibles: Int? = null,
    val latitud: Double? = null,
    val longitud: Double? = null,
    @SerializedName("velocidad_kmh") val velocidadKmh: Double? = null,
    val rumbo: Double? = null,
    val timestamp: String? = null,
    @SerializedName("edad_segundos") val edadSegundos: Int? = null,
)

data class FleetResponseDto(
    val total: Int? = null,
    @SerializedName("linea_id") val lineaId: Int? = null,
    val vehiculos: List<FleetVehicleDto>? = null,
)

// ------------------------------------------------------------------- Pagos
data class PagoQrRequestDto(
    @SerializedName("conductor_id") val conductorId: Int,
    @SerializedName("linea_id") val lineaId: Int,
    val monto: String,
)

data class PagoQrResponseDto(
    @SerializedName("codigo_qr_uuid") val codigoQrUuid: String? = null,
    val estado: String? = null,
    val monto: String? = null,
    @SerializedName("conductor_folio") val conductorFolio: String? = null,
    @SerializedName("linea_folio") val lineaFolio: Int? = null,
    @SerializedName("fecha_hora") val fechaHora: String? = null,
)

data class PagoConfirmarRequestDto(
    @SerializedName("codigo_qr_uuid") val codigoQrUuid: String,
)

data class PagoConfirmarResponseDto(
    @SerializedName("codigo_qr_uuid") val codigoQrUuid: String? = null,
    val estado: String? = null,
    val monto: String? = null,
)

data class TransaccionDto(
    val id: Int? = null,
    @SerializedName("codigo_qr_uuid") val codigoQrUuid: String? = null,
    val pasajero: Int? = null,
    @SerializedName("pasajero_rut") val pasajeroRut: String? = null,
    val conductor: Int? = null,
    @SerializedName("conductor_folio") val conductorFolio: String? = null,
    val linea: Int? = null,
    @SerializedName("linea_folio") val lineaFolio: Int? = null,
    val monto: String? = null,
    @SerializedName("fecha_hora") val fechaHora: String? = null,
    val estado: String? = null,
    @SerializedName("estado_display") val estadoDisplay: String? = null,
)

// --------------------------------------------------------------- Conductor
data class ConductorPerfilDto(
    val id: Int? = null,
    @SerializedName("usuario_id") val usuarioId: Int? = null,
    @SerializedName("usuario_nombre") val usuarioNombre: String? = null,
    @SerializedName("usuario_email") val usuarioEmail: String? = null,
    @SerializedName("usuario_rut") val usuarioRut: String? = null,
    @SerializedName("folio_conatacoch") val folioConatacoch: String? = null,
    val patente: String? = null,
    @SerializedName("marca_modelo") val marcaModelo: String? = null,
    @SerializedName("capacidad_pasajeros") val capacidadPasajeros: Int? = null,
    @SerializedName("linea_id") val lineaId: Int? = null,
    @SerializedName("linea_folio") val lineaFolio: Int? = null,
    @SerializedName("linea_nombre") val lineaNombre: String? = null,
    @SerializedName("en_turno") val enTurno: Boolean? = null,
    @SerializedName("cupos_disponibles") val cuposDisponibles: Int? = null,
    @SerializedName("otp_pendiente") val otpPendiente: Boolean? = null,
)

data class TurnoRequestDto(
    @SerializedName("solicitar_codigo") val solicitarCodigo: Boolean? = null,
    @SerializedName("codigo_otp") val codigoOtp: String? = null,
)

data class TurnoResponseDto(
    val estado: String? = null,
    val detail: String? = null,
    @SerializedName("codigo_otp") val codigoOtp: String? = null,
    @SerializedName("expires_in_minutes") val expiresInMinutes: Int? = null,
    val conductor: String? = null,
    val patente: String? = null,
    @SerializedName("en_turno") val enTurno: Boolean? = null,
    @SerializedName("cupos_disponibles") val cuposDisponibles: Int? = null,
    @SerializedName("token_sesion") val tokenSesion: String? = null,
)

data class CuposRequestDto(
    @SerializedName("cupos_disponibles") val cuposDisponibles: Int,
)

data class CuposResponseDto(
    val conductor: String? = null,
    @SerializedName("cupos_disponibles") val cuposDisponibles: Int? = null,
    @SerializedName("en_turno") val enTurno: Boolean? = null,
)

data class TelemetriaRequestDto(
    val latitud: Double,
    val longitud: Double,
    @SerializedName("velocidad_kmh") val velocidadKmh: Double,
    val rumbo: Double,
    @SerializedName("cupos_disponibles") val cuposDisponibles: Int,
    val timestamp: String,
)

data class TelemetriaResponseDto(
    @SerializedName("id_vehiculo") val idVehiculo: Int? = null,
    @SerializedName("velocidad_reportada_kmh") val velocidadReportadaKmh: Double? = null,
    @SerializedName("velocidad_calculada_kmh") val velocidadCalculadaKmh: Double? = null,
    @SerializedName("alerta_spoofing") val alertaSpoofing: Boolean? = null,
)
