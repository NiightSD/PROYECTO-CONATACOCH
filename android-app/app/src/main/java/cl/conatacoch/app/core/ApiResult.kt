package cl.conatacoch.app.core

import com.google.gson.JsonElement
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
        // DRF devuelve los errores de validacion dentro de "detail" como
        // objeto campo -> lista. Se aplanan para mostrarlos en la UI.
        val detail = flattenMessages(json.get("detail"))
        when {
            detail.isNotBlank() -> detail
            json.has("error") -> json.get("error").asString.replace('_', ' ')
            else -> "Error HTTP ${e.code()}"
        }
    }.getOrElse { "Error HTTP ${e.code()}" }
}

private fun flattenMessages(element: JsonElement?): String = when {
    element == null || element.isJsonNull -> ""
    element.isJsonPrimitive -> element.asString
    element.isJsonArray -> element.asJsonArray
        .mapNotNull { child -> flattenMessages(child).takeIf { it.isNotBlank() } }
        .distinct()
        .joinToString(" ")
    element.isJsonObject -> element.asJsonObject.entrySet()
        .mapNotNull { (_, value) -> flattenMessages(value).takeIf { it.isNotBlank() } }
        .distinct()
        .joinToString(" ")
    else -> ""
}
