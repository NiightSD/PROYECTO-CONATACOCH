package cl.conatacoch.app.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import cl.conatacoch.app.core.ServiceLocator
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class RegisterUiState(
    val rut: String = "",
    val nombre: String = "",
    val email: String = "",
    val password: String = "",
    val passwordConfirm: String = "",
    val loading: Boolean = false,
    val error: String? = null,
)

/**
 * Registro publico de pasajeros (POST /api/auth/registro/).
 *
 * El backend siempre asigna el rol CLIENTE. Al crear la cuenta devuelve los
 * tokens JWT, por lo que el usuario queda autenticado y AppRoot lo envia
 * directamente a la pantalla de pasajero.
 */
class RegisterViewModel : ViewModel() {

    private val authRepository = ServiceLocator.authRepository

    private val _state = MutableStateFlow(RegisterUiState())
    val state: StateFlow<RegisterUiState> = _state.asStateFlow()

    fun onRutChange(value: String) {
        _state.update { it.copy(rut = value.take(12), error = null) }
    }

    fun onNombreChange(value: String) {
        _state.update { it.copy(nombre = value.take(150), error = null) }
    }

    fun onEmailChange(value: String) {
        _state.update { it.copy(email = value.take(254), error = null) }
    }

    fun onPasswordChange(value: String) {
        _state.update { it.copy(password = value, error = null) }
    }

    fun onPasswordConfirmChange(value: String) {
        _state.update { it.copy(passwordConfirm = value, error = null) }
    }

    fun submit() {
        val snapshot = _state.value
        if (snapshot.loading) return

        val errorLocal = validar(snapshot)
        if (errorLocal != null) {
            _state.update { it.copy(error = errorLocal) }
            return
        }

        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            authRepository.register(
                rut = snapshot.rut,
                nombre = snapshot.nombre,
                email = snapshot.email,
                password = snapshot.password,
                passwordConfirm = snapshot.passwordConfirm,
            ).onSuccess {
                _state.update {
                    it.copy(loading = false, password = "", passwordConfirm = "")
                }
            }.onFailure { error ->
                _state.update {
                    it.copy(
                        loading = false,
                        error = error.message ?: "No se pudo crear la cuenta.",
                    )
                }
            }
        }
    }

    private fun validar(state: RegisterUiState): String? = when {
        state.rut.isBlank() -> "Ingresa tu RUT (ejemplo: 11.111.111-1)."
        state.nombre.isBlank() -> "Ingresa tu nombre completo."
        state.email.isBlank() || !state.email.contains("@") ->
            "Ingresa un email valido."
        state.password.length < 12 ->
            "La contraseña debe tener al menos 12 caracteres."
        state.password != state.passwordConfirm ->
            "Las contraseñas no coinciden."
        else -> null
    }
}
