package cl.conatacoch.app.core

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationManager

/**
 * Acceso a la ultima ubicacion conocida del dispositivo.
 *
 * La app no mantiene un servicio de ubicacion en segundo plano: usa el ultimo
 * fix disponible y, si no existe (emulador sin GPS), simula un desplazamiento
 * urbano alrededor de la ultima posicion o del centro de Santiago. Esto
 * mantiene el flujo de telemetria periodica funcionando en cualquier entorno
 * de demostracion sin bloquear la interfaz.
 */
class LocationTracker(private val context: Context) {

    fun hasPermission(): Boolean {
        val fine = context.checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = context.checkSelfPermission(android.Manifest.permission.ACCESS_COARSE_LOCATION)
        return fine == android.content.pm.PackageManager.PERMISSION_GRANTED ||
            coarse == android.content.pm.PackageManager.PERMISSION_GRANTED
    }

    @SuppressLint("MissingPermission")
    fun lastKnownLocation(): Pair<Double, Double>? {
        if (!hasPermission()) return null
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
            ?: return null
        val providers = listOf(
            LocationManager.GPS_PROVIDER,
            LocationManager.NETWORK_PROVIDER,
            LocationManager.PASSIVE_PROVIDER,
        )
        var best: Location? = null
        for (provider in providers) {
            val location = runCatching { manager.getLastKnownLocation(provider) }.getOrNull()
                ?: continue
            if (best == null || location.time > best.time) best = location
        }
        return best?.let { it.latitude to it.longitude }
    }

    companion object {
        val SANTIAGO: Pair<Double, Double> = -33.4489 to -70.6693
    }
}
