package cl.conatacoch.app

import android.app.Application
import android.content.Context
import cl.conatacoch.app.core.ServiceLocator
import org.osmdroid.config.Configuration

class ConatacochApp : Application() {

    override fun onCreate() {
        super.onCreate()
        ServiceLocator.init(this)

        Configuration.getInstance().apply {
            userAgentValue = packageName
            load(this@ConatacochApp, getSharedPreferences("osmdroid", Context.MODE_PRIVATE))
        }
    }
}
