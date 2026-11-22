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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import cl.conatacoch.app.BuildConfig
import cl.conatacoch.app.ui.components.ConaButton
import cl.conatacoch.app.ui.components.ConaCard
import cl.conatacoch.app.ui.components.ConaTextField
import cl.conatacoch.app.ui.components.ErrorBanner
import cl.conatacoch.app.ui.components.Kicker
import cl.conatacoch.app.ui.theme.ConaBlack
import cl.conatacoch.app.ui.theme.ConaMuted
import cl.conatacoch.app.ui.theme.ConaMutedSoft
import cl.conatacoch.app.ui.theme.ConaSurface
import cl.conatacoch.app.ui.theme.ConaWhite
import cl.conatacoch.app.ui.theme.ConaYellow

@Composable
fun LoginScreen(viewModel: LoginViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ConaBlack)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 28.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        BrandMark()

        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Kicker("CONATACOCH · Región Metropolitana")
            Text(
                text = buildAnnotatedString {
                    append("Muévete\n")
                    withStyle(SpanStyle(color = ConaYellow)) {
                        append("en amarillo.")
                    }
                },
                color = ConaWhite,
                style = MaterialTheme.typography.displayLarge,
            )
            Text(
                text = "Taxis y colectivos de Chile. Un solo acceso para pasajeros, conductores y administración.",
                color = ConaMuted,
                style = MaterialTheme.typography.bodyLarge,
            )
        }

        ConaCard {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    "Iniciar sesión",
                    color = ConaWhite,
                    style = MaterialTheme.typography.titleLarge,
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
                )

                TextButton(
                    onClick = viewModel::toggleOtpField,
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                ) {
                    Text(
                        if (state.showOtp) "Ocultar OTP de turno" else "Agregar OTP de turno (conductores)",
                        color = ConaYellow,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }

                if (state.showOtp) {
                    ConaTextField(
                        value = state.otp,
                        onValueChange = viewModel::onOtpChange,
                        label = "Código OTP de 6 dígitos",
                        keyboardType = KeyboardType.Number,
                        supportingText = "Opcional: activa tu turno si ya solicitaste el código.",
                    )
                }

                ErrorBanner(state.error)

                ConaButton(
                    text = if (state.loading) "Entrando…" else "Entrar",
                    onClick = viewModel::submit,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !state.loading,
                    tall = true,
                )

                Text(
                    "El rol se detecta automáticamente al autenticarse.",
                    color = ConaMutedSoft,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }

        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                "CREDENCIALES DEMO",
                color = ConaMutedSoft,
                style = MaterialTheme.typography.labelSmall,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                DemoChip("Pasajero", Modifier.weight(1f)) {
                    viewModel.useDemo("pasajero1@conatacoch.cl", "Pasajero2026!")
                }
                DemoChip("Conductor", Modifier.weight(1f)) {
                    viewModel.useDemo("conductor1@conatacoch.cl", "Conduc2026!")
                }
                DemoChip("Admin", Modifier.weight(1f)) {
                    viewModel.useDemo("admin@conatacoch.cl", "AdminConata2026!")
                }
            }
            Text(
                "API: ${BuildConfig.API_BASE_URL}",
                color = ConaMutedSoft,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun DemoChip(label: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        shape = RoundedCornerShape(50),
        modifier = modifier,
    ) {
        Text(
            label,
            color = ConaWhite,
            style = MaterialTheme.typography.bodySmall,
            maxLines = 1,
        )
    }
}

@Composable
private fun BrandMark() {
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
