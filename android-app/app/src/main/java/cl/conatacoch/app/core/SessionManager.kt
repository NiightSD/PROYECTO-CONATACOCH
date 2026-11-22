package cl.conatacoch.app.core

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import cl.conatacoch.app.domain.model.Session
import com.google.gson.Gson
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Persistencia de la sesion JWT.
 *
 * Usa EncryptedSharedPreferences (AES256-GCM) para no dejar los tokens en
 * texto plano. Si el keystore del dispositivo no esta disponible, cae a
 * SharedPreferences privadas para no romper el arranque de la app.
 */
class SessionManager(context: Context) {

    private val gson = Gson()
    private val prefs: SharedPreferences = createPrefs(context.applicationContext)

    private val _session = MutableStateFlow(loadSession())
    val session: StateFlow<Session?> = _session.asStateFlow()

    val current: Session? get() = _session.value

    fun currentAccessToken(): String? = _session.value?.access

    fun currentRefreshToken(): String? = _session.value?.refresh

    @Synchronized
    fun save(session: Session) {
        prefs.edit()
            .putString(KEY_SESSION, gson.toJson(session))
            .apply()
        _session.value = session
    }

    @Synchronized
    fun updateAccess(access: String) {
        val actual = _session.value ?: return
        val renovada = actual.copy(access = access)
        prefs.edit().putString(KEY_SESSION, gson.toJson(renovada)).apply()
        _session.value = renovada
    }

    @Synchronized
    fun clear() {
        prefs.edit().remove(KEY_SESSION).apply()
        _session.value = null
    }

    private fun loadSession(): Session? = runCatching {
        val raw = prefs.getString(KEY_SESSION, null) ?: return null
        gson.fromJson(raw, Session::class.java)
    }.getOrNull()

    private fun createPrefs(context: Context): SharedPreferences = runCatching {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            FILE_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }.getOrElse {
        context.getSharedPreferences(FALLBACK_FILE, Context.MODE_PRIVATE)
    }

    private companion object {
        const val FILE_NAME = "conatacoch_secure_session"
        const val FALLBACK_FILE = "conatacoch_session_fallback"
        const val KEY_SESSION = "session"
    }
}
