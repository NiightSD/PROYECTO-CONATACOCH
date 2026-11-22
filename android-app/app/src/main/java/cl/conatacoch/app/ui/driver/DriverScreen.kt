package cl.conatacoch.app.ui.driver

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import cl.conatacoch.app.core.Feedback
import cl.conatacoch.app.core.ServiceLocator
import cl.conatacoch.app.domain.model.Transaction
import cl.conatacoch.app.domain.model.User
import cl.conatacoch.app.ui.components.BrandBar
import cl.conatacoch.app.ui.components.ConaButton
import cl.conatacoch.app.ui.components.ConaCard
import cl.conatacoch.app.ui.components.ConaTextField
import cl.conatacoch.app.ui.components.ErrorBanner
import cl.conatacoch.app.ui.components.Kicker
import cl.conatacoch.app.ui.components.StatusChip
import cl.conatacoch.app.ui.theme.ConaBlack
import cl.conatacoch.app.ui.theme.ConaMuted
import cl.conatacoch.app.ui.theme.ConaMutedSoft
import cl.conatacoch.app.ui.theme.ConaOutline
import cl.conatacoch.app.ui.theme.ConaSurface
import cl.conatacoch.app.ui.theme.ConaWhite
import cl.conatacoch.app.ui.theme.ConaYellow
import java.text.NumberFormat
import java.util.Locale

@Composable
fun DriverScreen(
    user: User,
    viewModel: DriverViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions(),
    ) { }

    LaunchedEffect(Unit) {
        if (!ServiceLocator.locationTracker.hasPermission()) {
            permissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                )
            )
        }
    }

    // Alerta visual + sonora cuando llega un pago QR nuevo.
    LaunchedEffect(state.alertPayment?.uuid) {
        if (state.alertPayment != null) {
            Feedback.beep()
            Feedback.vibrate(ServiceLocator.appContext, 260)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ConaBlack),
    ) {
        BrandBar(
            roleLabel = "Conductor · ${user.nombre}",
            onLogout = { ServiceLocator.authRepository.logout() },
        )

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Column {
                    Kicker("Modo conducción")
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            "Tu turno",
                            color = ConaWhite,
                            style = MaterialTheme.typography.headlineLarge,
                        )
                        StatusChip(
                            text = if (state.enTurno) "En turno" else "Fuera de turno",
                            active = state.enTurno,
                        )
                    }
                }
            }

            item { VehicleCard(state) }
            item { ShiftCard(state, viewModel) }
            item { SeatCard(state, viewModel) }
            item { GpsCard(state, viewModel) }

            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        "Pagos QR pendientes",
                        color = ConaWhite,
                        style = MaterialTheme.typography.titleLarge,
                    )
                    StatusChip(
                        text = "${state.pending.size}",
                        active = state.pending.isNotEmpty(),
                    )
                }
            }

            if (state.pending.isEmpty()) {
                item {
                    Text(
                        "Sin pagos pendientes.",
                        color = ConaMutedSoft,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            } else {
                items(state.pending, key = { it.uuid }) { pago ->
                    PendingPaymentRow(
                        pago = pago,
                        enabled = !state.confirmingPayment,
                        onConfirm = { viewModel.confirmPayment(pago.uuid) },
                    )
                }
            }

            state.error?.let { message ->
                item { ErrorBanner(message) }
            }
        }
    }

    state.otpDialog?.let { dialog ->
        OtpDialog(
            dialog = dialog,
            confirming = state.confirmingOtp,
            onCodeChange = viewModel::onOtpChange,
            onConfirm = viewModel::confirmOtp,
            onDismiss = viewModel::dismissOtp,
        )
    }

    state.alertPayment?.let { pago ->
        PaymentAlertDialog(
            pago = pago,
            confirming = state.confirmingPayment,
            onConfirm = { viewModel.confirmPayment(pago.uuid) },
            onDismiss = viewModel::dismissAlert,
        )
    }
}

@Composable
private fun VehicleCard(state: DriverUiState) {
    val profile = state.profile
    ConaCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    "VEHÍCULO",
                    color = ConaMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
                Text(
                    profile?.patente ?: "—",
                    color = ConaWhite,
                    style = MaterialTheme.typography.headlineMedium,
                )
                Text(
                    "${profile?.lineaFolio ?: "—"} · ${profile?.lineaNombre ?: "Sin línea"}",
                    color = ConaMuted,
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    profile?.marcaModelo.orEmpty(),
                    color = ConaMutedSoft,
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "Folio ${profile?.folio ?: "—"}",
                    color = ConaMutedSoft,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    "CUPOS",
                    color = ConaMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
                Text(
                    "${state.cupos}",
                    color = ConaYellow,
                    style = MaterialTheme.typography.displayLarge,
                )
            }
        }
        if (state.loading) {
            LinearProgressIndicator(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp),
                color = ConaYellow,
                trackColor = ConaOutline,
            )
        }
    }
}

@Composable
private fun ShiftCard(state: DriverUiState, viewModel: DriverViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        ConaButton(
            text = when {
                state.requestingOtp -> "Solicitando OTP…"
                state.enTurno -> "Finalizar turno"
                else -> "Iniciar turno"
            },
            onClick = { viewModel.requestOtp(state.enTurno) },
            modifier = Modifier.fillMaxWidth(),
            enabled = !state.requestingOtp,
            tall = true,
        )
        ConaButton(
            text = if (state.gpsActive) "GPS activo · pausar" else "GPS apagado · activar",
            onClick = viewModel::toggleGps,
            modifier = Modifier.fillMaxWidth(),
            primary = false,
            enabled = state.enTurno,
            tall = true,
        )
        Text(
            if (state.enTurno) {
                "Turno activo. Mantén la app abierta para emitir telemetría y recibir pagos."
            } else {
                "Solicita tu código OTP de 6 dígitos para comenzar."
            },
            color = ConaMuted,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun SeatCard(state: DriverUiState, viewModel: DriverViewModel) {
    val capacidad = state.profile?.capacidad ?: 4
    ConaCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                "Asientos",
                color = ConaWhite,
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                if (state.cuposUpdating) "Guardando…" else "Switch rápido",
                color = ConaMutedSoft,
                style = MaterialTheme.typography.bodySmall,
            )
        }

        Spacer(Modifier.height(12.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(ConaBlack)
                .padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            SeatButton(
                text = "Disponible",
                selected = state.cupos > 0,
                modifier = Modifier.weight(1f),
                onClick = viewModel::markAvailable,
            )
            SeatButton(
                text = "Lleno",
                selected = state.cupos == 0,
                modifier = Modifier.weight(1f),
                onClick = viewModel::markFull,
            )
        }

        Spacer(Modifier.height(16.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            BigCircleButton(
                label = "−",
                enabled = state.cupos > 0,
                onClick = { viewModel.setCupos(state.cupos - 1) },
            )
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    "${state.cupos}",
                    color = ConaYellow,
                    fontSize = 56.sp,
                    fontWeight = FontWeight.Black,
                )
                Text(
                    "CUPOS LIBRES",
                    color = ConaMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
            BigCircleButton(
                label = "+",
                enabled = state.cupos < capacidad,
                onClick = { viewModel.setCupos(state.cupos + 1) },
            )
        }

        Text(
            "El cambio se envía a la API y viaja en la próxima telemetría.",
            modifier = Modifier.padding(top = 12.dp),
            color = ConaMutedSoft,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun GpsCard(state: DriverUiState, viewModel: DriverViewModel) {
    ConaCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                "Emisor GPS",
                color = ConaWhite,
                style = MaterialTheme.typography.titleMedium,
            )
            StatusChip(
                text = if (state.gpsActive) "Enviando" else "Detenido",
                active = state.gpsActive,
            )
        }
        Text(
            "Telemetría cada 5 s a /api/telemetria/enviar/",
            modifier = Modifier.padding(top = 4.dp),
            color = ConaMutedSoft,
            style = MaterialTheme.typography.bodySmall,
        )
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 10.dp),
            color = ConaBlack,
            shape = RoundedCornerShape(12.dp),
            border = BorderStroke(1.dp, ConaOutline),
        ) {
            Text(
                state.gpsReadout,
                modifier = Modifier.padding(12.dp),
                color = ConaYellow,
                fontFamily = FontFamily.Monospace,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        TextButton(
            onClick = viewModel::toggleGps,
            enabled = state.enTurno,
            modifier = Modifier.padding(top = 4.dp),
        ) {
            Text(
                if (state.gpsActive) "Pausar GPS" else "Activar GPS",
                color = if (state.enTurno) ConaYellow else ConaMutedSoft,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun SeatButton(
    text: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Surface(
        modifier = modifier
            .height(58.dp)
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick),
        color = if (selected) ConaYellow else Color.Transparent,
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                text,
                color = if (selected) ConaBlack else ConaWhite,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Black,
            )
        }
    }
}

@Composable
private fun BigCircleButton(
    label: String,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    Surface(
        modifier = Modifier
            .size(64.dp)
            .clip(CircleShape)
            .clickable(enabled = enabled, onClick = onClick),
        color = ConaSurface,
        border = BorderStroke(
            1.dp,
            if (enabled) ConaOutline else ConaOutline.copy(alpha = 0.4f),
        ),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                label,
                color = if (enabled) ConaWhite else ConaMutedSoft,
                fontSize = 30.sp,
                fontWeight = FontWeight.Black,
            )
        }
    }
}

@Composable
private fun PendingPaymentRow(
    pago: Transaction,
    enabled: Boolean,
    onConfirm: () -> Unit,
) {
    ConaCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    clp(pago.monto),
                    color = ConaWhite,
                    style = MaterialTheme.typography.titleLarge,
                )
                Text(
                    "${pago.pasajeroRut} · ${pago.uuid.take(8)}…",
                    color = ConaMuted,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            ConaButton(
                text = "Confirmar",
                onClick = onConfirm,
                enabled = enabled,
            )
        }
    }
}

@Composable
private fun OtpDialog(
    dialog: OtpDialogState,
    confirming: Boolean,
    onCodeChange: (String) -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = ConaSurface,
        titleContentColor = ConaWhite,
        textContentColor = ConaWhite,
        title = {
            Text(
                if (dialog.finalizar) "Finalizar turno" else "Iniciar turno",
                fontWeight = FontWeight.Black,
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    "Ingresa el código de 6 dígitos para confirmar la operación.",
                    color = ConaMuted,
                    style = MaterialTheme.typography.bodySmall,
                )
                dialog.codigoDemo?.let { codigo ->
                    Surface(
                        color = Color(0x1FFFD100),
                        shape = RoundedCornerShape(10.dp),
                        border = BorderStroke(1.dp, ConaYellow.copy(alpha = 0.5f)),
                    ) {
                        Text(
                            "Código demo: $codigo · expira en ${dialog.expiraMinutos} min",
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                            color = ConaYellow,
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }
                ConaTextField(
                    value = dialog.code,
                    onValueChange = onCodeChange,
                    label = "Código OTP",
                    keyboardType = KeyboardType.Number,
                )
                ErrorBanner(dialog.error)
            }
        },
        confirmButton = {
            TextButton(onClick = onConfirm, enabled = !confirming) {
                Text(
                    if (confirming) "Validando…" else "Confirmar",
                    color = ConaYellow,
                    style = MaterialTheme.typography.labelLarge,
                )
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancelar", color = ConaMuted)
            }
        },
    )
}

@Composable
private fun PaymentAlertDialog(
    pago: Transaction,
    confirming: Boolean,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = ConaYellow,
        titleContentColor = ConaBlack,
        textContentColor = ConaBlack,
        title = {
            Text("Pago QR recibido", fontWeight = FontWeight.Black)
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    clp(pago.monto),
                    color = ConaBlack,
                    style = MaterialTheme.typography.displayLarge,
                )
                Text(
                    "${pago.pasajeroRut} · ${pago.uuid.take(8)}…",
                    color = ConaBlack,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = onConfirm, enabled = !confirming) {
                Text(
                    if (confirming) "Confirmando…" else "Confirmar",
                    color = ConaBlack,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Black,
                )
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Descartar", color = ConaBlack)
            }
        },
    )
}

private fun clp(value: Double): String {
    val formatter = NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CL"))
    formatter.maximumFractionDigits = 0
    return "$" + formatter.format(value)
}
