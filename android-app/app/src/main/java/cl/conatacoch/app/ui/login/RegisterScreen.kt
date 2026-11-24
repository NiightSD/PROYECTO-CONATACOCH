package cl.conatacoch.app.ui.login

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import cl.conatacoch.app.ui.components.ConaButton
import cl.conatacoch.app.ui.components.ConaCard
import cl.conatacoch.app.ui.components.ConaTextField
import cl.conatacoch.app.ui.components.ErrorBanner
import cl.conatacoch.app.ui.components.Kicker
import cl.conatacoch.app.ui.theme.ConaBlack
import cl.conatacoch.app.ui.theme.ConaMuted
import cl.conatacoch.app.ui.theme.ConaMutedSoft
import cl.conatacoch.app.ui.theme.ConaWhite
import cl.conatacoch.app.ui.theme.ConaYellow

/**
 * Formulario de auto-registro para pasajeros. El backend crea la cuenta con
 * rol CLIENTE y devuelve los JWT, de modo que la sesion queda iniciada.
 */
@Composable
fun RegisterScreen(
    onBack: () -> Unit,
    viewModel: RegisterViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ConaBlack)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            RegisterBrandMark()
            TextButton(onClick = onBack) {
                Text("← Volver", color = ConaYellow, style = MaterialTheme.typography.labelLarge)
            }
        }

        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Kicker("CONATACOCH · Nueva cuenta")
            Text(
                "Crea tu cuenta\nde pasajero.",
                color = ConaWhite,
                style = MaterialTheme.typography.headlineLarge,
            )
            Text(
                "Registra tus datos para viajar, ver la flota en vivo y pagar con QR. Los conductores son registrados por el administrador.",
                color = ConaMuted,
                style = MaterialTheme.typography.bodyLarge,
            )
        }

        ConaCard {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    "Datos personales",
                    color = ConaWhite,
                    style = MaterialTheme.typography.titleLarge,
                )
                ConaTextField(
                    value = state.rut,
                    onValueChange = viewModel::onRutChange,
                    label = "RUT",
                    keyboardType = KeyboardType.Text,
                    supportingText = "Formato 11.111.111-1. Se valida el dígito verificador.",
                )
                ConaTextField(
                    value = state.nombre,
                    onValueChange = viewModel::onNombreChange,
                    label = "Nombre completo",
                )
                ConaTextField(
                    value = state.email,
                    onValueChange = viewModel::onEmailChange,
                    label = "Email",
                    keyboardType = KeyboardType.Email,
                )
                ConaTextField(
                    value = state.password,
                    onValueChange = viewModel::onPasswordChange,
                    label = "Contraseña",
                    keyboardType = KeyboardType.Password,
                    visualTransformation = PasswordVisualTransformation(),
                    supportingText = "Mínimo 12 caracteres, no numérica y no común.",
                )
                ConaTextField(
                    value = state.passwordConfirm,
                    onValueChange = viewModel::onPasswordConfirmChange,
                    label = "Repetir contraseña",
                    keyboardType = KeyboardType.Password,
                    visualTransformation = PasswordVisualTransformation(),
                )

                ErrorBanner(state.error)

                ConaButton(
                    text = if (state.loading) "Creando cuenta…" else "Crear cuenta",
                    onClick = viewModel::submit,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !state.loading,
                    tall = true,
                )
            }
        }

        Text(
            "Al crear la cuenta aceptas el uso de tus datos para operar el servicio de taxis y colectivos de CONATACOCH.",
            color = ConaMutedSoft,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun RegisterBrandMark() {
    Box(
        modifier = Modifier
            .size(56.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(ConaYellow),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            "C",
            color = ConaBlack,
            fontSize = 28.sp,
            fontWeight = FontWeight.Black,
        )
    }
}
