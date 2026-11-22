package cl.conatacoch.app.core

import com.google.gson.JsonParser
import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException

/** Error de API con mensaje legible para el usuario. */
class ApiException(message: String, val statusCode: Int = 0) : Exception(message)

/**
 * Ejecuta una llamada suspendida y transforma cualquier fallo en un
 * [Result] con mensaje util. Evita propagar excepciones a la capa UI.
 */
suspend fun <T> safeApiCall(block: suspend () -> T): Result<T> = try {
    Result.success(block())
} catch (e: HttpException) {
    Result.failure(ApiException(parseHttpError(e), e.code()))
} catch (e: SocketTimeoutException) {
    Result.failure(ApiException("La API tardó demasiado en responder.", 0))
} catch (e: IOException) {
    Result.failure(
        ApiException("No se pudo conectar con la API. Revisa la URL y la red.", 0)
    )
} catch (e: Exception) {
    Result.failure(ApiException(e.message ?: "Error inesperado.", 0))
}

private fun parseHttpError(e: HttpException): String {
    val body = runCatching { e.response()?.errorBody()?.string() }.getOrNull()
    if (body.isNullOrBlank()) return "Error HTTP ${e.code()}"
    return runCatching {
        val json = JsonParser.parseString(body).asJsonObject
        val detail = json.get("detail")
        when {
            detail != null && detail.isJsonArray ->
                detail.asJsonArray.joinToString(" ") { it.asString }
            detail != null && detail.isJsonPrimitive -> detail.asString
            json.has("error") -> json.get("error").asString.replace('_', ' ')
            else -> "Error HTTP ${e.code()}"
        }
    }.getOrElse { "Error HTTP ${e.code()}" }
}
