package cl.conatacoch.app.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cl.conatacoch.app.core.ServiceLocator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LoginUiState(
    val email: String = "",
    val password: String = "",
    val otp: String = "",
    val showOtp: Boolean = false,
    val loading: Boolean = false,
    val error: String? = null,
)

class LoginViewModel : ViewModel() {

    private val authRepository = ServiceLocator.authRepository
    private val driverRepository = ServiceLocator.driverRepository

    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    fun onEmailChange(value: String) {
        _state.update { it.copy(email = value, error = null) }
    }

    fun onPasswordChange(value: String) {
        _state.update { it.copy(password = value, error = null) }
    }

    fun onOtpChange(value: String) {
        val digits = value.filter { it.isDigit() }.take(6)
        _state.update { it.copy(otp = digits, error = null) }
    }

    fun toggleOtpField() {
        _state.update { it.copy(showOtp = !it.showOtp) }
    }

    fun useDemo(email: String, password: String) {
        _state.update { it.copy(email = email, password = password, error = null) }
    }

    fun submit() {
        val snapshot = _state.value
        if (snapshot.loading) return
        if (snapshot.email.isBlank() || snapshot.password.isBlank()) {
            _state.update { it.copy(error = "Ingresa tu email y contraseña.") }
            return
        }

        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val result = authRepository.login(snapshot.email, snapshot.password)
            result.onSuccess { session ->
                _state.update { it.copy(loading = false, password = "") }
                // OTP opcional: si el conductor ya tenia un codigo solicitado,
                // se intenta activar el turno de inmediato.
                if (session.user.isDriver && snapshot.otp.length == 6) {
                    driverRepository.confirmarTurno(snapshot.otp, finalizar = false)
                }
            }.onFailure { error ->
                _state.update {
                    it.copy(
                        loading = false,
                        error = error.message ?: "No se pudo iniciar sesión.",
                    )
                }
            }
        }
    }
}
