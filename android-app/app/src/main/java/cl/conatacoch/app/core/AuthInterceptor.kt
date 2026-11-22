package cl.conatacoch.app.core

import okhttp3.Interceptor
import okhttp3.Response

/** Agrega el header Authorization Bearer a cada request autenticado. */
class AuthInterceptor(
    private val sessionManager: SessionManager,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val token = sessionManager.currentAccessToken()
        val request = if (token.isNullOrBlank()) {
            chain.request()
        } else {
            chain.request().newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        }
        return chain.proceed(request)
    }
}
