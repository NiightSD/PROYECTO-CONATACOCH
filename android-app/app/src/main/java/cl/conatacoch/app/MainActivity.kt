package cl.conatacoch.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import cl.conatacoch.app.ui.AppRoot
import cl.conatacoch.app.ui.theme.ConatacochTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ConatacochTheme {
                AppRoot()
            }
        }
    }
}
