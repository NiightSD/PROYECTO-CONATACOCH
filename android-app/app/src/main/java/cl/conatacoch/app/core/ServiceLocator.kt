package cl.conatacoch.app.core

import android.content.Context
import cl.conatacoch.app.data.repository.AuthRepositoryImpl
import cl.conatacoch.app.data.repository.DriverRepositoryImpl
import cl.conatacoch.app.data.repository.PassengerRepositoryImpl
import cl.conatacoch.app.domain.repository.AuthRepository
import cl.conatacoch.app.domain.repository.DriverRepository
import cl.conatacoch.app.domain.repository.PassengerRepository

/**
 * Inyeccion de dependencias manual (suficiente para el tamano de la app).
 * Se inicializa una sola vez desde [cl.conatacoch.app.ConatacochApp].
 */
object ServiceLocator {

    @Volatile
    private var initialized = false

    lateinit var appContext: Context
        private set

    lateinit var sessionManager: SessionManager
        private set

    lateinit var authRepository: AuthRepository
        private set

    lateinit var passengerRepository: PassengerRepository
        private set

    lateinit var driverRepository: DriverRepository
        private set

    lateinit var locationTracker: LocationTracker
        private set

    fun init(context: Context) {
        if (initialized) return
        synchronized(this) {
            if (initialized) return
            val app = context.applicationContext
            appContext = app
            sessionManager = SessionManager(app)
            val api = NetworkModule.createApi(sessionManager)
            authRepository = AuthRepositoryImpl(api, sessionManager)
            passengerRepository = PassengerRepositoryImpl(api)
            driverRepository = DriverRepositoryImpl(api)
            locationTracker = LocationTracker(app)
            initialized = true
        }
    }
}
