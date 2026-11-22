package cl.conatacoch.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val ConaColorScheme = darkColorScheme(
    primary = ConaYellow,
    onPrimary = ConaBlack,
    primaryContainer = ConaYellow,
    onPrimaryContainer = ConaBlack,
    secondary = ConaWhite,
    onSecondary = ConaBlack,
    secondaryContainer = ConaSurfaceHigh,
    onSecondaryContainer = ConaWhite,
    tertiary = ConaYellow,
    onTertiary = ConaBlack,
    background = ConaBlack,
    onBackground = ConaWhite,
    surface = ConaBlack,
    onSurface = ConaWhite,
    surfaceVariant = ConaSurface,
    onSurfaceVariant = ConaMuted,
    surfaceContainer = ConaSurface,
    surfaceContainerHigh = ConaSurfaceHigh,
    outline = ConaOutline,
    outlineVariant = ConaOutlineStrong,
    error = ConaWhite,
    onError = ConaBlack,
    errorContainer = ConaSurfaceHigh,
    onErrorContainer = ConaWhite,
    scrim = ConaBlack,
)

@Composable
fun ConatacochTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = ConaColorScheme,
        typography = ConaTypography,
        content = content,
    )
}
