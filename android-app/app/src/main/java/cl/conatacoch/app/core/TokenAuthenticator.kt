package cl.conatacoch.app.core

import cl.conatacoch.app.data.remote.ApiService
import cl.conatacoch.app.data.remote.dto.RefreshRequestDto
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

/**
 * Renueva el access token cuando la API responde 401.
 *
 * Usa un cliente Retrofit "plano" (sin este Authenticator) para evitar
 * recursion infinita. Si el refresh falla, la sesion se limpia.
 */
class TokenAuthenticator(
    private val sessionManager: SessionManager,
    private val refreshApi: ApiService,
) : Authenticator {

    override fun authenticate(route: Route?, response: Response): Request? {
        val original = response.request
        if (original.header("Authorization").isNullOrBlank()) return null
        if (responseCount(response) >= 2) return null

        synchronized(this) {
            val failedToken = original.header("Authorization")
                ?.removePrefix("Bearer ")
                ?.trim()
            val currentToken = sessionManager.currentAccessToken()

            // Otro hilo ya renovo el token.
            if (!currentToken.isNullOrBlank() && currentToken != failedToken) {
                return original.newBuilder()
                    .header("Authorization", "Bearer $currentToken")
                    .build()
            }

            val refresh = sessionManager.currentRefreshToken() ?: return null
            val nuevoAccess = runCatching {
                runBlocking { refreshApi.refresh(RefreshRequestDto(refresh)).access }
            }.getOrNull()

            if (nuevoAccess.isNullOrBlank()) {
                sessionManager.clear()
                return null
            }

            sessionManager.updateAccess(nuevoAccess)
            return original.newBuilder()
                .header("Authorization", "Bearer $nuevoAccess")
                .build()
        }
    }

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) {
            count += 1
            prior = prior.priorResponse
        }
        return count
    }
}
