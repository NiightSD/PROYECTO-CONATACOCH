package cl.conatacoch.app.data.repository

import cl.conatacoch.app.core.SessionManager
import cl.conatacoch.app.core.safeApiCall
import cl.conatacoch.app.data.remote.ApiService
import cl.conatacoch.app.data.remote.dto.LoginRequestDto
import cl.conatacoch.app.data.remote.dto.RegistroRequestDto
import cl.conatacoch.app.data.remote.dto.toSession
import cl.conatacoch.app.domain.model.Session
import cl.conatacoch.app.domain.repository.AuthRepository
import kotlinx.coroutines.flow.StateFlow

class AuthRepositoryImpl(
    private val api: ApiService,
    private val sessionManager: SessionManager,
) : AuthRepository {

    override fun session(): StateFlow<Session?> = sessionManager.session

    override suspend fun login(email: String, password: String): Result<Session> = safeApiCall {
        val response = api.login(
            LoginRequestDto(
                email = email.trim().lowercase(),
                password = password,
            )
        )
        val session = response.toSession()
            ?: throw IllegalStateException("Respuesta de login incompleta.")
        sessionManager.save(session)
        session
    }

    override suspend fun register(
        rut: String,
        nombre: String,
        email: String,
        password: String,
        passwordConfirm: String,
    ): Result<Session> = safeApiCall {
        val response = api.registrar(
            RegistroRequestDto(
                rut = rut.trim(),
                nombre = nombre.trim(),
                email = email.trim().lowercase(),
                password = password,
                passwordConfirm = passwordConfirm,
            )
        )
        val session = response.toSession()
            ?: throw IllegalStateException("Respuesta de registro incompleta.")
        sessionManager.save(session)
        session
    }

    override fun logout() {
        sessionManager.clear()
    }
}
