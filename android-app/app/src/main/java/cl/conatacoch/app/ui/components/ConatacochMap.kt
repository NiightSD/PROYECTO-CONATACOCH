package cl.conatacoch.app.ui.components

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import cl.conatacoch.app.R
import cl.conatacoch.app.domain.model.FleetVehicle
import org.osmdroid.tileprovider.tilesource.XYTileSource
import org.osmdroid.util.BoundingBox
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker

/**
 * Mapa OSMDroid con tema oscuro alineado a la paleta CONATACOCH.
 *
 * Muestra la flota en vivo (marcadores amarillos) y, si existe, la ubicacion
 * del pasajero (marcador blanco). La primera vez ajusta el zoom a los puntos.
 */
@Composable
fun ConatacochMap(
    vehicles: List<FleetVehicle>,
    userLocation: Pair<Double, Double>?,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val fitted = remember { mutableStateOf(false) }
    val mapView = remember {
        MapView(context).apply {
            setTileSource(darkTileSource())
            setMultiTouchControls(true)
            setUseDataConnection(true)
            controller.setZoom(12.0)
            controller.setCenter(GeoPoint(-33.4489, -70.6693))
        }
    }
    val lifecycleOwner = LocalLifecycleOwner.current

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            mapView.onDetach()
        }
    }

    AndroidView(
        factory = { mapView },
        modifier = modifier,
        update = { map ->
            map.overlays.clear()
            val vehicleIcon = ContextCompat.getDrawable(context, R.drawable.ic_vehicle_marker)
            val userIcon = ContextCompat.getDrawable(context, R.drawable.ic_user_marker)
            val points = mutableListOf<GeoPoint>()

            userLocation?.let { (lat, lng) ->
                val point = GeoPoint(lat, lng)
                points.add(point)
                Marker(map).apply {
                    position = point
                    icon = userIcon
                    setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
                    title = "Tu ubicación"
                }.also { map.overlays.add(it) }
            }

            vehicles.forEach { vehicle ->
                val point = GeoPoint(vehicle.latitud, vehicle.longitud)
                points.add(point)
                Marker(map).apply {
                    position = point
                    icon = vehicleIcon
                    setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
                    title = "${vehicle.patente} · ${vehicle.folio}"
                    snippet = "${vehicle.lineaNombre} · ${vehicle.cupos} cupos"
                    setOnMarkerClickListener { marker, _ ->
                        marker.showInfoWindow()
                        true
                    }
                }.also { map.overlays.add(it) }
            }

            if (points.isNotEmpty() && !fitted.value) {
                if (points.size == 1) {
                    map.controller.setZoom(14.0)
                    map.controller.setCenter(points.first())
                } else {
                    map.zoomToBoundingBox(
                        BoundingBox.fromGeoPoints(points),
                        true,
                        72,
                    )
                }
                fitted.value = true
            }
            map.invalidate()
        },
    )
}

private fun darkTileSource(): XYTileSource = XYTileSource(
    "CartoDark",
    0,
    19,
    256,
    ".png",
    arrayOf(
        "https://a.basemaps.cartocdn.com/dark_all/",
        "https://b.basemaps.cartocdn.com/dark_all/",
        "https://c.basemaps.cartocdn.com/dark_all/",
    ),
)
