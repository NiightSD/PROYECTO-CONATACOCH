package cl.conatacoch.app.ui.passenger

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import cl.conatacoch.app.core.QrUtils
import cl.conatacoch.app.core.ServiceLocator
import cl.conatacoch.app.domain.model.FleetVehicle
import cl.conatacoch.app.domain.model.Linea
import cl.conatacoch.app.domain.model.QrPayment
import cl.conatacoch.app.domain.model.User
import cl.conatacoch.app.ui.components.BrandBar
import cl.conatacoch.app.ui.components.ConaButton
import cl.conatacoch.app.ui.components.ConaCard
import cl.conatacoch.app.ui.components.ConaTextField
import cl.conatacoch.app.ui.components.ConatacochMap
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
fun PassengerScreen(
    user: User,
    viewModel: PassengerViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions(),
    ) { viewModel.refreshLocation() }

    LaunchedEffect(Unit) {
        if (ServiceLocator.locationTracker.hasPermission()) {
            viewModel.refreshLocation()
        } else {
            permissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                )
            )
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ConaBlack),
    ) {
        BrandBar(
            roleLabel = "${user.roleLabel} · ${user.nombre}",
            onLogout = { ServiceLocator.authRepository.logout() },
        )

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Column {
                    Kicker("Pasajero")
                    Text(
                        "¿Dónde vas?",
                        color = ConaWhite,
                        style = MaterialTheme.typography.headlineLarge,
                    )
                }
            }

            item {
                ConaCard {
                    ConaTextField(
                        value = state.query,
                        onValueChange = viewModel::onQueryChange,
                        label = "Buscar folio, comuna o recorrido",
                    )
                    if (state.searching) {
                        LinearProgressIndicator(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 10.dp),
                            color = ConaYellow,
                            trackColor = ConaOutline,
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Catálogo oficial CONATACOCH · datos en vivo de la API",
                        color = ConaMutedSoft,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            if (state.results.isNotEmpty()) {
                item {
                    ConaCard {
                        Text(
                            "RESULTADOS",
                            color = ConaMuted,
                            style = MaterialTheme.typography.labelSmall,
                        )
                        state.results.take(8).forEachIndexed { index, linea ->
                            if (index > 0) {
                                HorizontalDivider(
                                    modifier = Modifier.padding(vertical = 2.dp),
                                    color = ConaOutline,
                                )
                            }
                            ResultRow(linea = linea, onClick = { viewModel.selectLinea(linea) })
                        }
                    }
                }
            }

            state.selected?.let { linea ->
                item {
                    SelectedRouteCard(
                        linea = linea,
                        loading = state.loading,
                        onRefresh = viewModel::refresh,
                    )
                }
            }

            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(260.dp)
                        .clip(RoundedCornerShape(20.dp))
                        .border(1.dp, ConaOutline, RoundedCornerShape(20.dp)),
                ) {
                    ConatacochMap(
                        vehicles = state.fleet,
                        userLocation = state.userLocation,
                        modifier = Modifier.fillMaxSize(),
                    )
                    Surface(
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(10.dp),
                        color = ConaBlack.copy(alpha = 0.88f),
                        shape = RoundedCornerShape(50),
                        border = BorderStroke(1.dp, ConaYellow.copy(alpha = 0.5f)),
                    ) {
                        Text(
                            "● ${state.fleet.size} en vivo",
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                            color = ConaYellow,
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                }
            }

            item {
                EtaCard(state = state, onPay = viewModel::requestPayment)
            }

            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        "Colectivos activos",
                        color = ConaWhite,
                        style = MaterialTheme.typography.titleLarge,
                    )
                    Text(
                        "${state.fleet.size} en línea",
                        color = ConaMutedSoft,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            if (state.fleet.isEmpty()) {
                item {
                    Text(
                        "Sin colectivos con telemetría reciente.",
                        color = ConaMutedSoft,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            } else {
                items(state.fleet, key = { "${it.conductorId}-${it.patente}" }) { vehicle ->
                    FleetRow(vehicle)
                }
            }

            state.error?.let { message ->
                item { ErrorBanner(message) }
            }
        }
    }

    if (state.showPaymentConfirm) {
        PaymentConfirmDialog(
            state = state,
            onMontoChange = viewModel::onMontoChange,
            onConfirm = viewModel::createPayment,
            onDismiss = viewModel::cancelPaymentConfirm,
        )
    }

    state.payment?.let { payment ->
        QrDialog(
            payment = payment,
            status = state.paymentStatus,
            onClose = viewModel::dismissPayment,
        )
    }
}

@Composable
private fun ResultRow(linea: Linea, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            "#${linea.folio}",
            color = ConaYellow,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Black,
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                linea.nombreRecorrido,
                color = ConaWhite,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold,
                maxLines = 2,
            )
            Text(
                "${linea.comunaOrigen} → ${linea.comunaDestino}",
                color = ConaMuted,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        Text("›", color = ConaMuted, fontSize = 20.sp)
    }
}

@Composable
private fun SelectedRouteCard(linea: Linea, loading: Boolean, onRefresh: () -> Unit) {
    ConaCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            StatusChip(linea.tipoTrazado, active = true)
            TextButton(onClick = onRefresh, enabled = !loading) {
                Text(
                    if (loading) "Actualizando…" else "Actualizar",
                    color = ConaYellow,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        Text(
            "#${linea.folio} · ${linea.nombreRecorrido}",
            color = ConaWhite,
            style = MaterialTheme.typography.titleLarge,
        )
        Text(
            "${linea.comunaOrigen} → ${linea.comunaDestino}",
            color = ConaMuted,
            style = MaterialTheme.typography.bodySmall,
        )
        HorizontalDivider(
            modifier = Modifier.padding(vertical = 10.dp),
            color = ConaOutline,
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                clp(linea.tarifaActual),
                color = ConaWhite,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Black,
            )
            Text(
                linea.domicilioOrigen,
                color = ConaMuted,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun EtaCard(state: PassengerUiState, onPay: () -> Unit) {
    val nearest = state.eta?.nearest
    ConaCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                "ETA más cercano",
                color = ConaWhite,
                style = MaterialTheme.typography.titleMedium,
            )
            StatusChip(
                text = if (nearest != null) "En vivo" else "Sin unidades",
                active = nearest != null,
            )
        }

        if (nearest == null) {
            Text(
                "No hay colectivos con telemetría reciente para este recorrido.",
                modifier = Modifier.padding(top = 8.dp),
                color = ConaMuted,
                style = MaterialTheme.typography.bodySmall,
            )
            if (state.loading) {
                LinearProgressIndicator(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 10.dp),
                    color = ConaYellow,
                    trackColor = ConaOutline,
                )
            }
            return@ConaCard
        }

        Row(
            modifier = Modifier.padding(top = 6.dp),
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                String.format(Locale.US, "%.1f", nearest.etaMinutos),
                color = ConaWhite,
                style = MaterialTheme.typography.displayLarge,
            )
            Text(
                "min",
                modifier = Modifier.padding(bottom = 8.dp),
                color = ConaYellow,
                style = MaterialTheme.typography.labelLarge,
            )
        }
        Text(
            "${nearest.patente} · ${String.format(Locale.US, "%.2f", nearest.distanciaKm)} km · ${nearest.cupos} cupos",
            color = ConaMuted,
            style = MaterialTheme.typography.bodySmall,
        )

        state.eta?.options
            ?.filter { it.conductorId != nearest.conductorId }
            ?.take(3)
            ?.forEach { option ->
                HorizontalDivider(
                    modifier = Modifier.padding(vertical = 6.dp),
                    color = ConaOutline,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        "${option.patente} · ${option.folio}",
                        color = ConaWhite,
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        "${option.etaMinutos} min",
                        color = ConaYellow,
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }

        Spacer(Modifier.height(10.dp))
        ConaButton(
            text = if (state.paying) "Generando QR…" else "Pagar con QR",
            onClick = onPay,
            modifier = Modifier.fillMaxWidth(),
            enabled = !state.paying,
            tall = true,
        )
    }
}

@Composable
private fun FleetRow(vehicle: FleetVehicle) {
    ConaCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(ConaYellow),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "TX",
                    color = ConaBlack,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Black,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    vehicle.patente,
                    color = ConaWhite,
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    "${vehicle.folio} · ${vehicle.lineaNombre}",
                    color = ConaMuted,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    "${vehicle.cupos}",
                    color = ConaYellow,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Black,
                )
                Text(
                    "cupos",
                    color = ConaMutedSoft,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}

@Composable
private fun PaymentConfirmDialog(
    state: PassengerUiState,
    onMontoChange: (String) -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    val nearest = state.eta?.nearest
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = ConaSurface,
        titleContentColor = ConaWhite,
        textContentColor = ConaWhite,
        title = { Text("Confirmar pago") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    "Pagarás ${clp(state.monto)} a ${nearest?.patente ?: "el conductor"} " +
                        "(${nearest?.folio ?: "sin folio"}).",
                    color = ConaMuted,
                    style = MaterialTheme.typography.bodyMedium,
                )
                ConaTextField(
                    value = state.montoText,
                    onValueChange = onMontoChange,
                    label = "Monto CLP",
                    keyboardType = KeyboardType.Number,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = onConfirm) {
                Text(
                    "Pagar ahora",
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
private fun QrDialog(payment: QrPayment, status: String, onClose: () -> Unit) {
    val image = remember(payment.uuid) {
        QrUtils.generate(payment.uuid)?.asImageBitmap()
    }
    AlertDialog(
        onDismissRequest = onClose,
        containerColor = ConaSurface,
        titleContentColor = ConaWhite,
        textContentColor = ConaWhite,
        title = { Text("QR de pago") },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                if (image != null) {
                    Image(
                        bitmap = image,
                        contentDescription = "Código QR de pago",
                        modifier = Modifier.size(220.dp),
                        contentScale = ContentScale.Fit,
                    )
                } else {
                    Text(
                        "No se pudo dibujar el QR.",
                        color = ConaMuted,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Text(
                    payment.uuid,
                    color = ConaMutedSoft,
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "Monto: ${clp(payment.monto)} · ${payment.conductorFolio}",
                    color = ConaWhite,
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    status,
                    color = ConaYellow,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = onClose) {
                Text("Cerrar", color = ConaYellow, style = MaterialTheme.typography.labelLarge)
            }
        },
    )
}

private fun clp(value: Double): String {
    val formatter = NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CL"))
    formatter.maximumFractionDigits = 0
    return "$" + formatter.format(value)
}
