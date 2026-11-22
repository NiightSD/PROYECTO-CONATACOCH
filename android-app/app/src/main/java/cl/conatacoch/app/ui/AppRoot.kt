package cl.conatacoch.app.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import cl.conatacoch.app.core.ServiceLocator
import cl.conatacoch.app.ui.admin.AdminScreen
import cl.conatacoch.app.ui.driver.DriverScreen
import cl.conatacoch.app.ui.login.LoginScreen
import cl.conatacoch.app.ui.passenger.PassengerScreen

/**
 * Punto de entrada de la UI. La sesion (StateFlow) decide el destino segun el
 * rol que devuelve el backend: CONDUCTOR, ADMIN o CLIENTE.
 */
@Composable
fun AppRoot() {
    val session by ServiceLocator.sessionManager.session.collectAsStateWithLifecycle()
    val current = session

    when {
        current == null -> LoginScreen()
        current.user.isDriver -> DriverScreen(user = current.user)
        current.user.isAdmin -> AdminScreen(user = current.user)
        else -> PassengerScreen(user = current.user)
    }
}
