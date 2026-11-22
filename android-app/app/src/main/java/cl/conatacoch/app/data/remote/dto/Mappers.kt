package cl.conatacoch.app.data.remote.dto

import cl.conatacoch.app.domain.model.DriverProfile
import cl.conatacoch.app.domain.model.EtaOption
import cl.conatacoch.app.domain.model.EtaResult
import cl.conatacoch.app.domain.model.FleetVehicle
import cl.conatacoch.app.domain.model.Linea
import cl.conatacoch.app.domain.model.Paradero
import cl.conatacoch.app.domain.model.QrPayment
import cl.conatacoch.app.domain.model.Session
import cl.conatacoch.app.domain.model.TelemetryAck
import cl.conatacoch.app.domain.model.Transaction
import cl.conatacoch.app.domain.model.TurnoOtp
import cl.conatacoch.app.domain.model.User

fun UsuarioDto.toDomain(): User = User(
    id = id ?: 0,
    rut = rut.orEmpty(),
    nombre = nombre.orEmpty(),
    email = email.orEmpty(),
    rol = rol ?: "CLIENTE",
)

fun LoginResponseDto.toSession(): Session? {
    val token = access ?: return null
    val refreshToken = refresh ?: return null
    val userDto = usuario ?: return null
    return Session(access = token, refresh = refreshToken, user = userDto.toDomain())
}

fun LineaDto.toDomain(): Linea = Linea(
    id = id ?: 0,
    folio = folio ?: 0,
    nombreRecorrido = nombreRecorrido.orEmpty(),
    tipoTrazado = tipoTrazado ?: "PRINCIPAL",
    comunaOrigen = comunaOrigen.orEmpty(),
    comunaDestino = comunaDestino.orEmpty(),
    domicilioOrigen = domicilioOrigen.orEmpty(),
    domicilioDestino = domicilioDestino.orEmpty(),
    tarifaActual = tarifaActual?.toDoubleOrNull() ?: 0.0,
)

fun ParaderoDto.toDomain(): Paradero? {
    val lat = latitud?.toDoubleOrNull() ?: return null
    val lng = longitud?.toDoubleOrNull() ?: return null
    return Paradero(
        id = id ?: 0,
        nombre = nombre.orEmpty(),
        comuna = comuna.orEmpty(),
        latitud = lat,
        longitud = lng,
    )
}

fun EtaOptionDto.toDomain(): EtaOption? {
    val idConductor = conductorId ?: return null
    return EtaOption(
        conductorId = idConductor,
        folio = folioConatacoch.orEmpty(),
        patente = patente.orEmpty(),
        distanciaKm = distanciaKm ?: 0.0,
        etaMinutos = etaMinutos ?: (etaSegundos ?: 0) / 60.0,
        cupos = cuposDisponibles ?: 0,
    )
}

fun EtaResponseDto.toDomain(): EtaResult = EtaResult(
    lineaId = lineaId ?: 0,
    nombreRecorrido = nombreRecorrido.orEmpty(),
    nearest = conductorMasCercano?.toDomain(),
    options = opciones.orEmpty().mapNotNull { it.toDomain() },
)

fun FleetVehicleDto.toDomain(): FleetVehicle? {
    val lat = latitud ?: return null
    val lng = longitud ?: return null
    return FleetVehicle(
        conductorId = conductorId ?: 0,
        folio = folioConatacoch.orEmpty(),
        patente = patente.orEmpty(),
        lineaNombre = lineaNombre.orEmpty(),
        cupos = cuposDisponibles ?: 0,
        latitud = lat,
        longitud = lng,
        velocidadKmh = velocidadKmh ?: 0.0,
        edadSegundos = edadSegundos,
    )
}

fun PagoQrResponseDto.toDomain(): QrPayment = QrPayment(
    uuid = codigoQrUuid.orEmpty(),
    estado = estado ?: "PENDIENTE",
    monto = monto?.toDoubleOrNull() ?: 0.0,
    conductorFolio = conductorFolio.orEmpty(),
    lineaFolio = lineaFolio ?: 0,
)

fun TransaccionDto.toDomain(): Transaction = Transaction(
    id = id ?: 0,
    uuid = codigoQrUuid.orEmpty(),
    monto = monto?.toDoubleOrNull() ?: 0.0,
    estado = estado ?: "",
    estadoDisplay = estadoDisplay ?: estado.orEmpty(),
    pasajeroRut = pasajeroRut.orEmpty(),
    conductorFolio = conductorFolio.orEmpty(),
    lineaFolio = lineaFolio ?: 0,
    fechaHora = fechaHora.orEmpty(),
)

fun ConductorPerfilDto.toDomain(): DriverProfile = DriverProfile(
    id = id ?: 0,
    nombre = usuarioNombre.orEmpty(),
    rut = usuarioRut.orEmpty(),
    folio = folioConatacoch.orEmpty(),
    patente = patente.orEmpty(),
    marcaModelo = marcaModelo.orEmpty(),
    capacidad = capacidadPasajeros ?: 4,
    lineaId = lineaId ?: 0,
    lineaFolio = lineaFolio ?: 0,
    lineaNombre = lineaNombre.orEmpty(),
    enTurno = enTurno ?: false,
    cupos = cuposDisponibles ?: 0,
)

fun TurnoResponseDto.toOtp(): TurnoOtp = TurnoOtp(
    codigo = codigoOtp,
    expiraMinutos = expiresInMinutes ?: 5,
    detail = detail.orEmpty(),
)

fun TelemetriaResponseDto.toDomain(): TelemetryAck = TelemetryAck(
    velocidadCalculada = velocidadCalculadaKmh ?: 0.0,
    alertaSpoofing = alertaSpoofing ?: false,
)
