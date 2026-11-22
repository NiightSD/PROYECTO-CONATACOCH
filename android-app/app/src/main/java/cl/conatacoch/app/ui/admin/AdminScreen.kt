package cl.conatacoch.app.ui.admin

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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import cl.conatacoch.app.core.ServiceLocator
import cl.conatacoch.app.domain.model.User
import cl.conatacoch.app.ui.components.BrandBar
import cl.conatacoch.app.ui.components.ConaButton
import cl.conatacoch.app.ui.components.ConaCard
import cl.conatacoch.app.ui.components.KeyValueRow
import cl.conatacoch.app.ui.components.Kicker
import cl.conatacoch.app.ui.theme.ConaBlack
import cl.conatacoch.app.ui.theme.ConaMuted
import cl.conatacoch.app.ui.theme.ConaMutedSoft
import cl.conatacoch.app.ui.theme.ConaOutline
import cl.conatacoch.app.ui.theme.ConaWhite
import cl.conatacoch.app.ui.theme.ConaYellow

/**
 * Vista movil del administrador.
 *
 * La operacion completa (CRUD de lineas, tarifas, flota y auditoria QR) vive
 * en el panel web mobile-first; aqui se entrega identidad, rol y accesos.
 */
@Composable
fun AdminScreen(user: User) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ConaBlack),
    ) {
        BrandBar(
            roleLabel = "Administrador · ${user.nombre}",
            onLogout = { ServiceLocator.authRepository.logout() },
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Column {
                Kicker("Administración")
                Text(
                    "Panel administrativo",
                    color = ConaWhite,
                    style = MaterialTheme.typography.headlineLarge,
                )
            }

            Text(
                "La gestión completa de líneas, tarifas, flota y auditoría QR está " +
                    "disponible en el panel web mobile-first (web-admin/), servido por Nginx " +
                    "junto a la misma API.",
                color = ConaMuted,
                style = MaterialTheme.typography.bodyLarge,
            )

            ConaCard {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Box(
                        modifier = Modifier
                            .size(52.dp)
                            .clip(RoundedCornerShape(16.dp))
                            .background(ConaYellow),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            "ADM",
                            color = ConaBlack,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Black,
                        )
                    }
                    Column {
                        Text(
                            user.nombre,
                            color = ConaWhite,
                            style = MaterialTheme.typography.titleLarge,
                        )
                        Text(
                            user.email,
                            color = ConaMuted,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
                HorizontalDivider(
                    modifier = Modifier.padding(vertical = 12.dp),
                    color = ConaOutline,
                )
                KeyValueRow("RUT", user.rut.ifBlank { "—" })
                KeyValueRow("Rol", user.roleLabel)
                KeyValueRow("Sesión", "JWT activo")
            }

            ConaCard {
                Text(
                    "Accesos de operación",
                    color = ConaWhite,
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    "• Panel web: web-admin/ (Nginx)\n" +
                        "• Swagger: /api/docs/\n" +
                        "• Django Admin: /admin/",
                    modifier = Modifier.padding(top = 8.dp),
                    color = ConaMuted,
                    style = MaterialTheme.typography.bodySmall,
                )
            }

            ConaButton(
                text = "Cerrar sesión",
                onClick = { ServiceLocator.authRepository.logout() },
                modifier = Modifier.fillMaxWidth(),
                primary = false,
                tall = true,
            )

            Text(
                "CONATACOCH · Fase 3",
                color = ConaMutedSoft,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
