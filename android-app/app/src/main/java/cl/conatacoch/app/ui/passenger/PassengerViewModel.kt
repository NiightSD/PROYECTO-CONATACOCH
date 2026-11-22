package cl.conatacoch.app.ui.passenger

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cl.conatacoch.app.core.LocationTracker
import cl.conatacoch.app.core.ServiceLocator
import cl.conatacoch.app.domain.model.EtaResult
import cl.conatacoch.app.domain.model.FleetVehicle
import cl.conatacoch.app.domain.model.Linea
import cl.conatacoch.app.domain.model.Paradero
import cl.conatacoch.app.domain.model.QrPayment
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

data class PassengerUiState(
    val query: String = "",
    val results: List<Linea> = emptyList(),
    val searching: Boolean = false,
    val selected: Linea? = null,
    val paraderos: List<Paradero> = emptyList(),
    val fleet: List<FleetVehicle> = emptyList(),
    val eta: EtaResult? = null,
    val loading: Boolean = false,
    val error: String? = null,
    val userLocation: Pair<Double, Double>? = null,
    val showPaymentConfirm: Boolean = false,
    val montoText: String = "1000",
    val paying: Boolean = false,
    val payment: QrPayment? = null,
    val paymentStatus: String = "",
) {
    val monto: Double get() = montoText.toDoubleOrNull() ?: 0.0
}

class PassengerViewModel : ViewModel() {

    private val repository = ServiceLocator.passengerRepository
    private val locationTracker = ServiceLocator.locationTracker

    private val _state = MutableStateFlow(PassengerUiState())
    val state: StateFlow<PassengerUiState> = _state.asStateFlow()

    private var searchJob: Job? = null
    private var refreshJob: Job? = null
    private var paymentJob: Job? = null

    init {
        refreshLocation()
        viewModelScope.launch { runSearch("") }
    }

    fun refreshLocation() {
        _state.update { it.copy(userLocation = locationTracker.lastKnownLocation()) }
    }

    fun onQueryChange(value: String) {
        _state.update { it.copy(query = value, error = null) }
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(350)
            runSearch(value)
        }
    }

    private suspend fun runSearch(query: String) {
        _state.update { it.copy(searching = true, error = null) }
        repository.buscarLineas(query)
            .onSuccess { lineas ->
                _state.update { it.copy(results = lineas, searching = false) }
            }
            .onFailure { error ->
                _state.update {
                    it.copy(searching = false, error = error.message ?: "No se pudo buscar.")
                }
            }
    }

    fun selectLinea(linea: Linea) {
        viewModelScope.launch { loadLinea(linea) }
    }

    private suspend fun loadLinea(linea: Linea) {
        _state.update {
            it.copy(
                selected = linea,
                query = linea.displayName,
                results = emptyList(),
                loading = true,
                error = null,
                eta = null,
                paraderos = emptyList(),
                fleet = emptyList(),
            )
        }

        val paraderos = repository.paraderos(linea.id).getOrElse { emptyList() }
        val fleet = repository.flota(linea.id).getOrElse { emptyList() }
        val location = locationTracker.lastKnownLocation()
            ?: paraderos.firstOrNull()?.let { it.latitud to it.longitud }
            ?: LocationTracker.SANTIAGO

        val etaResult = repository.eta(linea.id, location.first, location.second)
        _state.update {
            it.copy(
                selected = linea,
                paraderos = paraderos,
                fleet = fleet,
                userLocation = location,
                eta = etaResult.getOrNull(),
                loading = false,
                error = etaResult.exceptionOrNull()?.message,
            )
        }
        startAutoRefresh(linea)
    }

    fun refresh() {
        val linea = _state.value.selected ?: return
        viewModelScope.launch { loadLinea(linea) }
    }

    private fun startAutoRefresh(linea: Linea) {
        refreshJob?.cancel()
        refreshJob = viewModelScope.launch {
            while (isActive) {
                delay(12_000)
                val location = _state.value.userLocation ?: LocationTracker.SANTIAGO
                val fleet = repository.flota(linea.id).getOrNull() ?: continue
                val eta = repository.eta(linea.id, location.first, location.second).getOrNull()
                _state.update { it.copy(fleet = fleet, eta = eta ?: it.eta) }
            }
        }
    }

    // ------------------------------------------------------------- Pago QR
    fun requestPayment() {
        val snapshot = _state.value
        val nearest = snapshot.eta?.nearest
        if (snapshot.selected == null || nearest == null) {
            _state.update {
                it.copy(error = "Selecciona un recorrido con colectivos disponibles.")
            }
            return
        }
        val monto = snapshot.selected.tarifaActual.takeIf { it > 0 } ?: 1000.0
        _state.update {
            it.copy(
                showPaymentConfirm = true,
                montoText = monto.toInt().toString(),
                error = null,
            )
        }
    }

    fun onMontoChange(value: String) {
        val digits = value.filter { it.isDigit() }.take(7)
        _state.update { it.copy(montoText = digits) }
    }

    fun cancelPaymentConfirm() {
        _state.update { it.copy(showPaymentConfirm = false) }
    }

    fun createPayment() {
        val snapshot = _state.value
        val nearest = snapshot.eta?.nearest ?: return
        val selected = snapshot.selected ?: return
        val monto = snapshot.monto
        if (monto <= 0) {
            _state.update { it.copy(error = "Ingresa un monto válido.") }
            return
        }

        viewModelScope.launch {
            _state.update { it.copy(paying = true, showPaymentConfirm = false, error = null) }
            repository.crearPago(nearest.conductorId, selected.id, monto)
                .onSuccess { payment ->
                    _state.update {
                        it.copy(
                            paying = false,
                            payment = payment,
                            paymentStatus = "Pendiente de confirmación del conductor.",
                        )
                    }
                    pollPayment(payment.uuid)
                }
                .onFailure { error ->
                    _state.update {
                        it.copy(paying = false, error = error.message ?: "No se pudo crear el pago.")
                    }
                }
        }
    }

    private fun pollPayment(uuid: String) {
        paymentJob?.cancel()
        paymentJob = viewModelScope.launch {
            repeat(60) {
                delay(3_000)
                val transaccion = repository.buscarTransaccion(uuid).getOrNull() ?: return@repeat
                when (transaccion.estado) {
                    "PAGADO" -> {
                        _state.update {
                            it.copy(paymentStatus = "Pago confirmado por el conductor.")
                        }
                        return@launch
                    }
                    "ANULADO", "EXPIRADO" -> {
                        _state.update {
                            it.copy(paymentStatus = "Pago ${transaccion.estado.lowercase()}.")
                        }
                        return@launch
                    }
                    else -> _state.update {
                        it.copy(paymentStatus = "Pendiente de confirmación del conductor.")
                    }
                }
            }
        }
    }

    fun dismissPayment() {
        paymentJob?.cancel()
        paymentJob = null
        _state.update { it.copy(payment = null, paymentStatus = "") }
    }

    fun dismissError() {
        _state.update { it.copy(error = null) }
    }

    override fun onCleared() {
        searchJob?.cancel()
        refreshJob?.cancel()
        paymentJob?.cancel()
        super.onCleared()
    }
}
