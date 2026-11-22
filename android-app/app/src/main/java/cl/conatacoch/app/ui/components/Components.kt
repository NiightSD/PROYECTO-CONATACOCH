package cl.conatacoch.app.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import cl.conatacoch.app.ui.theme.ConaBlack
import cl.conatacoch.app.ui.theme.ConaMuted
import cl.conatacoch.app.ui.theme.ConaMutedSoft
import cl.conatacoch.app.ui.theme.ConaOutline
import cl.conatacoch.app.ui.theme.ConaSurface
import cl.conatacoch.app.ui.theme.ConaWhite
import cl.conatacoch.app.ui.theme.ConaYellow
import cl.conatacoch.app.ui.theme.ConaYellowSoft

@Composable
fun ConaCard(
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = ConaSurface,
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, ConaOutline),
    ) {
        Column(modifier = Modifier.padding(16.dp), content = content)
    }
}

@Composable
fun ConaButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    primary: Boolean = true,
    tall: Boolean = false,
) {
    val height = if (tall) 60.dp else 50.dp
    if (primary) {
        Button(
            onClick = onClick,
            modifier = modifier.heightIn(min = height),
            enabled = enabled,
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = ConaYellow,
                contentColor = ConaBlack,
                disabledContainerColor = ConaYellow.copy(alpha = 0.32f),
                disabledContentColor = ConaBlack.copy(alpha = 0.6f),
            ),
        ) {
            Text(text, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Black)
        }
    } else {
        OutlinedButton(
            onClick = onClick,
            modifier = modifier.heightIn(min = height),
            enabled = enabled,
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, ConaOutline),
            colors = ButtonDefaults.outlinedButtonColors(
                contentColor = ConaWhite,
                disabledContentColor = ConaMutedSoft,
            ),
        ) {
            Text(text, style = MaterialTheme.typography.labelLarge)
        }
    }
}

@Composable
fun ConaTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    singleLine: Boolean = true,
    keyboardType: KeyboardType = KeyboardType.Text,
    visualTransformation: VisualTransformation = VisualTransformation.None,
    supportingText: String? = null,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier.fillMaxWidth(),
        enabled = enabled,
        singleLine = singleLine,
        label = { Text(label) },
        supportingText = if (supportingText != null) {
            { Text(supportingText, color = ConaMuted) }
        } else {
            null
        },
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        visualTransformation = visualTransformation,
        shape = RoundedCornerShape(14.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedTextColor = ConaWhite,
            unfocusedTextColor = ConaWhite,
            disabledTextColor = ConaMutedSoft,
            focusedBorderColor = ConaYellow,
            unfocusedBorderColor = ConaOutline,
            disabledBorderColor = ConaOutline,
            focusedLabelColor = ConaYellow,
            unfocusedLabelColor = ConaMuted,
            disabledLabelColor = ConaMutedSoft,
            cursorColor = ConaYellow,
            focusedContainerColor = ConaBlack,
            unfocusedContainerColor = ConaBlack,
            disabledContainerColor = ConaBlack,
        ),
    )
}

@Composable
fun Kicker(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text.uppercase(),
        modifier = modifier,
        color = ConaYellow,
        style = MaterialTheme.typography.labelSmall,
    )
}

@Composable
fun StatusChip(text: String, active: Boolean, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        color = if (active) ConaYellowSoft else ConaSurface,
        shape = RoundedCornerShape(50),
        border = BorderStroke(1.dp, if (active) ConaYellow.copy(alpha = 0.5f) else ConaOutline),
    ) {
        Text(
            text = text.uppercase(),
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            color = if (active) ConaYellow else ConaMuted,
            style = MaterialTheme.typography.labelSmall,
        )
    }
}

@Composable
fun BrandBar(
    roleLabel: String,
    onLogout: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(
            modifier = Modifier
                .size(42.dp)
                .clip(RoundedCornerShape(13.dp))
                .background(ConaYellow),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                "C",
                color = ConaBlack,
                fontSize = 20.sp,
                fontWeight = FontWeight.Black,
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                "CONATACOCH",
                color = ConaWhite,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Black,
                letterSpacing = 2.sp,
            )
            Text(
                roleLabel,
                color = ConaMuted,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        TextButton(onClick = onLogout) {
            Text("Salir", color = ConaYellow, style = MaterialTheme.typography.labelLarge)
        }
    }
}

@Composable
fun ErrorBanner(message: String?, modifier: Modifier = Modifier) {
    if (message.isNullOrBlank()) return
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = Color(0xFF2A1010),
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, Color(0xFF7A2A2A)),
    ) {
        Text(
            text = message,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            color = ConaWhite,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
fun KeyValueRow(label: String, value: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = ConaMuted, style = MaterialTheme.typography.bodySmall)
        Text(value, color = ConaWhite, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
    }
}
