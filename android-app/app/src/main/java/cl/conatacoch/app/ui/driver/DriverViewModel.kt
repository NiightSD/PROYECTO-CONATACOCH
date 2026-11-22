package cl.conatacoch.app.ui.driver

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cl.conatacoch.app.core.LocationTracker
import cl.conatacoch.app.core.ServiceLocator
import cl.conatacoch.app.domain.model.DriverProfile
import cl.conatacoch.app.domain.model.Transaction
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.Locale

data class OtpDialogState(
    val finalizar: Boolean,
    val codigoDemo: String?,
    val expiraMinutos: Int,
    val code: String = "",
    val error: String? = null,
)

data class DriverUiState(
    val loading: Boolean = true,
    val profile: DriverProfile? = null,
    val enTurno: Boolean = false,
    val cupos: Int = 4,
    val error: String? = null,
    val otpDialog: OtpDialogState? = null,
    val requestingOtp: Boolean = false,
    val confirmingOtp: Boolean = false,
    val gpsActive: Boolean = false,
    val gpsReadout: String = "Sin envíos",
    val pending: List<Transaction> = emptyList(),
    val alertPayment: Transaction? = null,
    val confirmingPayment: Boolean = false,
    val cuposUpdating: Boolean = false,
)

class DriverViewModel : ViewModel() {

    private val repository = ServiceLocator.driverRepository
    private val locationTracker = ServiceLocator.locationTracker

    private val _state = MutableStateFlow(DriverUiState())
    val state: StateFlow<DriverUiState> = _state.asStateFlow()

    private var gpsJob: Job? = null
    private var pendingJob: Job? = null
    private val seenPayments = mutableSetOf<String>()
    private var pendingInitialized = false

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            repository.perfil()
                .onSuccess { profile ->
                    _state.update {
                        it.copy(
                            loading = false,
                            profile = profile,
                            enTurno = profile.enTurno,
                            cupos = if (profile.enTurno) profile.cupos else profile.capacidad,
                        )
                    }
                    if (profile.enTurno) {
                        startGpsIfNeeded()
                        startPendingPolling()
                    } else {
                        stopGps()
                        stopPendingPolling()
                    }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(
                            loading = false,
                            error = error.message ?: "No se pudo cargar el perfil.",
                        )
                    }
                }
        }
    }

    // ------------------------------------------------------------------ OTP
    fun requestOtp(finalizar: Boolean) {
        if (finalizar && !_state.value.enTurno) {
            _state.update { it.copy(error = "No tienes un turno activo.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(requestingOtp = true, error = null) }
            repository.solicitarOtp(finalizar)
                .onSuccess { otp ->
                    if (otp.codigo.isNullOrBlank()) {
                        _state.update {
                            it.copy(
                                requestingOtp = false,
                                error = otp.detail.ifBlank { "No se pudo solicitar el código." },
                            )
                        }
                        refresh()
                    } else {
                        _state.update {
                            it.copy(
                                requestingOtp = false,
                                otpDialog = OtpDialogState(
                                    finalizar = finalizar,
                                    codigoDemo = otp.codigo,
                                    expiraMinutos = otp.expiraMinutos,
                                ),
                            )
                        }
                    }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(
                            requestingOtp = false,
                            error = error.message ?: "No se pudo solicitar el OTP.",
                        )
                    }
                }
        }
    }

    fun onOtpChange(value: String) {
        val digits = value.filter { it.isDigit() }.take(6)
        _state.update { state ->
            val dialog = state.otpDialog ?: return@update state
            state.copy(otpDialog = dialog.copy(code = digits, error = null))
        }
    }

    fun confirmOtp() {
        val dialog = _state.value.otpDialog ?: return
        if (dialog.code.length != 6) {
            _state.update {
                it.copy(otpDialog = dialog.copy(error = "El código debe tener 6 dígitos."))
            }
            return
        }

        viewModelScope.launch {
            _state.update { it.copy(confirmingOtp = true) }
            repository.confirmarTurno(dialog.code, dialog.finalizar)
                .onSuccess {
                    _state.update { it.copy(confirmingOtp = false, otpDialog = null) }
                    if (dialog.finalizar) {
                        seenPayments.clear()
                        pendingInitialized = false
                        _state.update {
                            it.copy(enTurno = false, cupos = 0, gpsActive = false, pending = emptyList())
                        }
                        stopGps()
                        stopPendingPolling()
                    } else {
                        val capacidad = _state.value.profile?.capacidad ?: 4
                        repository.actualizarCupos(capacidad)
                        _state.update {
                            it.copy(
                                enTurno = true,
                                cupos = capacidad,
                                alertPayment = null,
                                pending = emptyList(),
                            )
                        }
                        startGpsIfNeeded()
                        startPendingPolling()
                    }
                    refresh()
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(
                            confirmingOtp = false,
                            otpDialog = dialog.copy(
                                error = error.message ?: "Código OTP inválido.",
                            ),
                        )
                    }
                }
        }
    }

    fun dismissOtp() {
        _state.update { it.copy(otpDialog = null) }
    }

    // ---------------------------------------------------------------- Cupos
    fun setCupos(value: Int) {
        val capacidad = _state.value.profile?.capacidad ?: 4
        val next = value.coerceIn(0, capacidad)
        _state.update { it.copy(cupos = next) }

        if (!_state.value.enTurno) return

        viewModelScope.launch {
            _state.update { it.copy(cuposUpdating = true) }
            repository.actualizarCupos(next)
                .onSuccess { saved ->
                    _state.update { it.copy(cupos = saved, cuposUpdating = false) }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(
                            cuposUpdating = false,
                            error = error.message ?: "No se pudieron actualizar los cupos.",
                        )
                    }
                }
        }
    }

    fun markAvailable() {
        setCupos(_state.value.profile?.capacidad ?: 4)
    }

    fun markFull() {
        setCupos(0)
    }

    // ------------------------------------------------------------------ GPS
    fun toggleGps() {
        if (gpsJob?.isActive == true) {
            stopGps()
        } else {
            startGpsIfNeeded()
        }
    }

    private fun startGpsIfNeeded() {
        if (gpsJob?.isActive == true) return
        if (_state.value.profile == null || !_state.value.enTurno) return

        gpsJob = viewModelScope.launch {
            _state.update { it.copy(gpsActive = true) }
            var position = locationTracker.lastKnownLocation() ?: LocationTracker.SANTIAGO
            var tick = 0

            while (isActive) {
                if (!_state.value.enTurno) break
                tick += 1
                val angle = (tick * 11) % 360
                val radians = Math.toRadians(angle.toDouble())
                position = (position.first + Math.cos(radians) * 0.00012) to
                    (position.second + Math.sin(radians) * 0.0001)
                val speed = 24.0 + (tick % 4) * 3

                val result = repository.enviarTelemetria(
                    latitud = position.first,
                    longitud = position.second,
                    velocidadKmh = speed,
                    rumbo = angle.toDouble(),
                    cupos = _state.value.cupos,
                )
                result.onSuccess { ack ->
                    _state.update {
                        it.copy(
                            gpsReadout = String.format(
                                Locale.US,
                                "%.5f, %.5f · %.0f km/h · %d cupos",
                                position.first,
                                position.second,
                                ack.velocidadCalculada,
                                it.cupos,
                            )
                        )
                    }
                }.onFailure { error ->
                    _state.update { it.copy(gpsReadout = "Error GPS: ${error.message}") }
                }

                delay(5_000)
            }
            _state.update { it.copy(gpsActive = false) }
        }
    }

    private fun stopGps() {
        gpsJob?.cancel()
        gpsJob = null
        _state.update { it.copy(gpsActive = false) }
    }

    // --------------------------------------------------------------- Pagos
    private fun startPendingPolling() {
        if (pendingJob?.isActive == true) return
        pendingJob = viewModelScope.launch {
            while (isActive) {
                val profile = _state.value.profile ?: break
                if (!_state.value.enTurno) break

                val pagos = repository.pagosPendientes(profile.id).getOrNull()
                if (pagos != null) {
                    _state.update { it.copy(pending = pagos) }
                    if (!pendingInitialized) {
                        seenPayments.addAll(pagos.map { it.uuid })
                        pendingInitialized = true
                    } else {
                        val nuevo = pagos.firstOrNull { it.uuid !in seenPayments }
                        if (nuevo != null) {
                            seenPayments.add(nuevo.uuid)
                            _state.update { it.copy(alertPayment = nuevo) }
                        }
                    }
                }
                delay(5_000)
            }
        }
    }

    private fun stopPendingPolling() {
        pendingJob?.cancel()
        pendingJob = null
    }

    fun confirmPayment(uuid: String) {
        viewModelScope.launch {
            _state.update { it.copy(confirmingPayment = true) }
            repository.confirmarPago(uuid)
                .onSuccess {
                    seenPayments.add(uuid)
                    _state.update { state ->
                        state.copy(
                            confirmingPayment = false,
                            pending = state.pending.filter { it.uuid != uuid },
                            alertPayment = if (state.alertPayment?.uuid == uuid) {
                                null
                            } else {
                                state.alertPayment
                            },
                        )
                    }
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(
                            confirmingPayment = false,
                            error = error.message ?: "No se pudo confirmar el pago.",
                        )
                    }
                }
        }
    }

    fun dismissAlert() {
        _state.update { it.copy(alertPayment = null) }
    }

    fun dismissError() {
        _state.update { it.copy(error = null) }
    }

    override fun onCleared() {
        gpsJob?.cancel()
        pendingJob?.cancel()
        super.onCleared()
    }
}
