# CONATACOCH Android — Fase 3

Aplicación nativa **Kotlin + Jetpack Compose** para pasajeros, conductores y
administradores de CONATACOCH. Consume la misma API REST del backend Django y
respeta la identidad visual de la marca: **negro `#0B0B0B`, blanco `#FFFFFF` y
amarillo `#FFD100`**.

> **Estado:** proyecto compilado y verificado localmente con
> `.\gradlew.bat :app:assembleDebug` → `BUILD SUCCESSFUL`. APK generado en
> `app/build/outputs/apk/debug/app-debug.apk`.

---

## 1. Funcionalidades

### 1.1 Acceso unificado

- Un solo formulario de login (`POST /api/auth/login/`).
- El rol se detecta desde la respuesta del backend (`CONDUCTOR`, `ADMIN`,
  `CLIENTE`) y la app navega automáticamente a la pantalla correspondiente.
- Campo OTP opcional de 6 dígitos para que un conductor active su turno justo
  después de autenticarse.
- Credenciales demo precargables con un toque.
- JWT persistido con `EncryptedSharedPreferences` (AES-256-GCM) y renovación
  automática mediante `TokenAuthenticator` cuando la API responde `401`.

### 1.2 Pasajero

- Búsqueda de recorridos por folio, comuna o nombre (`GET /api/lineas/`).
- Mapa **OSMDroid** con tema oscuro, marcador del pasajero y marcadores de la
  flota en vivo (`GET /api/telemetria/flota/?linea_id=`).
- Tarjeta de **ETA más cercano**: minutos, distancia, patente y cupos
  (`POST /api/eta/calcular/`).
- Actualización automática cada 12 segundos.
- Pago QR en dos toques: confirmar monto → generar QR local con ZXing
  (`POST /api/pagos/qr/`) → estado pendiente/confirmado consultando
  `/api/transacciones/?search=<uuid>`.
- Visualización de cupos y listado de colectivos activos.

### 1.3 Conductor (modo oscuro de alto contraste)

- Pantalla pensada para uso con una mano y botones grandes (mínimo 50–64 dp).
- Perfil y vehículo desde `GET /api/conductor/perfil/`.
- **Inicio y cierre de turno con OTP**:
  `POST /api/conductor/iniciar-turno/` y
  `POST /api/conductor/finalizar-turno/` con `solicitar_codigo=true`.
- **Cambio de cupos/asientos** con botones `−` / `+`, atajos
  *Disponible* / *Lleno* y sincronización con `POST /api/conductor/cupos/`.
- **Emisor GPS periódico** cada 5 s a `POST /api/telemetria/enviar/` usando la
  última ubicación conocida del dispositivo (o un desplazamiento simulado si el
  emulador no tiene fix GPS).
- **Alerta de pago QR** visual + sonora (`ToneGenerator`) + vibración cuando
  aparece un pago pendiente nuevo; confirmación con un toque
  (`POST /api/pagos/confirmar/`).

### 1.4 Administrador

- Identidad, rol y estado de sesión.
- Accesos directos al panel web mobile-first (`web-admin/`), Swagger
  (`/api/docs/`) y Django Admin (`/admin/`).
- El CRUD completo de líneas, tarifas, flota y auditoría QR vive en el panel
  web, que es la superficie operativa recomendada para escritorio.

---

## 2. Arquitectura (MVVM + Clean Architecture)

```text
app/src/main/java/cl/conatacoch/app/
├── ConatacochApp.kt              Application: ServiceLocator + OSMDroid
├── MainActivity.kt               ComponentActivity + Compose
├── core/
│   ├── ApiResult.kt              safeApiCall + mensajes de error legibles
│   ├── AuthInterceptor.kt        Agrega Authorization: Bearer <access>
│   ├── TokenAuthenticator.kt     Refresh automático ante 401
│   ├── SessionManager.kt         Persistencia cifrada de la sesión
│   ├── NetworkModule.kt          Retrofit + OkHttp + logging
│   ├── ServiceLocator.kt         Inyección de dependencias manual
│   ├── LocationTracker.kt        Última ubicación conocida
│   ├── Feedback.kt               Tono, vibración
│   └── QrUtils.kt                Render local del QR (ZXing)
├── domain/
│   ├── model/Models.kt           Entidades de negocio
│   └── repository/Repositories.kt  Contratos Auth / Passenger / Driver
├── data/
│   ├── remote/
│   │   ├── ApiService.kt         Endpoints Retrofit
│   │   └── dto/                  DTOs + mappers a dominio
│   └── repository/               Implementaciones de repositorio
└── ui/
    ├── AppRoot.kt                Router por rol
    ├── theme/                    Colores, tipografía, MaterialTheme
    ├── components/               Cards, botones, campos, mapa OSMDroid
    ├── login/                    LoginScreen + LoginViewModel
    ├── passenger/                PassengerScreen + PassengerViewModel
    ├── driver/                   DriverScreen + DriverViewModel
    └── admin/                    AdminScreen
```

**Regla de dependencias:** `ui → domain ← data`. La capa `ui` solo conoce
interfaces de repositorio; `data` implementa esas interfaces con Retrofit.

| Capa | Responsabilidad |
|---|---|
| `ui` | Estado de pantalla (`StateFlow`), eventos y composición Compose |
| `domain` | Modelos puros y contratos de repositorio |
| `data` | DTOs, mappers, Retrofit, persistencia de sesión |
| `core` | Infraestructura transversal (red, sesión, GPS, feedback) |

Los `ViewModel` no reciben argumentos de constructor y resuelven sus
dependencias desde `ServiceLocator`, lo que permite `viewModel()` de Compose sin
fábricas personalizadas.

---

## 3. Stack y versiones

| Componente | Versión |
|---|---|
| Kotlin | 2.0.21 |
| Android Gradle Plugin | 8.7.3 |
| Gradle | 8.9 |
| compileSdk / targetSdk | 35 |
| minSdk | 24 (Android 7.0) |
| Jetpack Compose BOM | 2024.12.01 |
| Material Design | Material 3 |
| Retrofit / OkHttp | 2.11.0 / 4.12.0 |
| Coroutines | 1.9.0 |
| OSMDroid | 6.1.20 |
| ZXing core | 3.5.3 |
| Security Crypto | 1.1.0-alpha06 |

---

## 4. Configuración de la URL de la API

La URL se inyecta en `BuildConfig.API_BASE_URL` desde `gradle.properties`:

```properties
CONATACOCH_API_BASE_URL=http://10.0.2.2:8000/api/
```

| Entorno | Valor recomendado |
|---|---|
| Emulador Android + backend local | `http://10.0.2.2:8000/api/` |
| Dispositivo físico en la misma LAN | `http://<IP-del-PC>:8000/api/` |
| Producción tras Nginx | `https://<dominio>/api/` |

También se puede definir en `local.properties`:

```properties
CONATACOCH_API_BASE_URL=http://192.168.1.50:8000/api/
```

`local.properties` está ignorado por Git. La app permite tráfico HTTP en claro
**solo** para desarrollo mediante `network_security_config.xml`; en producción
usar HTTPS.

---

## 5. Compilar y ejecutar

### 5.1 Requisitos

- Android Studio Ladybug o superior (o JDK 17 + Android SDK).
- SDK Platform 35 y Build-Tools 34+.
- Backend CONATACOCH accesible.

### 5.2 Línea de comandos

```powershell
cd android-app

# Windows
.\gradlew.bat :app:assembleDebug

# Linux / macOS
./gradlew :app:assembleDebug
```

APK resultante:

```text
android-app/app/build/outputs/apk/debug/app-debug.apk
```

Instalar en un emulador o dispositivo conectado:

```powershell
.\gradlew.bat :app:installDebug
# o
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

### 5.3 Android Studio

1. **File → Open** y seleccionar la carpeta `android-app/`.
2. Esperar la sincronización de Gradle (descarga dependencias la primera vez).
3. Crear un dispositivo virtual (API 34/35) o conectar un teléfono con
   depuración USB.
4. Verificar que el backend esté arriba y que `CONATACOCH_API_BASE_URL` apunte
   al host correcto.
5. **Run ▶**.

Si se usa el backend con `docker-compose.dev.yml`, está expuesto en
`http://localhost:8000`; desde el emulador se accede como
`http://10.0.2.2:8000`.

---

## 6. Credenciales demo

| Rol | Email | Password |
|---|---|---|
| Pasajero | `pasajero1@conatacoch.cl` | `Pasajero2026!` |
| Conductor | `conductor1@conatacoch.cl` | `Conduc2026!` |
| Administrador | `admin@conatacoch.cl` | `AdminConata2026!` |

Las credenciales demo se pueden cargar desde la pantalla de login. No usar en
producción.

---

## 7. Endpoints consumidos

| Método | Endpoint | Uso en la app |
|---|---|---|
| POST | `/api/auth/login/` | Login unificado y detección de rol |
| POST | `/api/auth/refresh/` | Renovación automática de JWT |
| GET | `/api/lineas/` | Búsqueda de recorridos |
| GET | `/api/paraderos/?linea=` | Paraderos del recorrido |
| GET | `/api/vehiculos/?linea=` | Flota de la línea |
| GET | `/api/telemetria/flota/` | Mapa de flota en vivo |
| POST | `/api/eta/calcular/` | ETA del colectivo más cercano |
| POST | `/api/pagos/qr/` | Crear pago QR (pasajero) |
| POST | `/api/pagos/confirmar/` | Confirmar pago (conductor) |
| GET | `/api/transacciones/` | Estado del pago y pagos pendientes |
| GET | `/api/conductor/perfil/` | Perfil del conductor autenticado |
| POST | `/api/conductor/iniciar-turno/` | Solicitar/validar OTP de inicio |
| POST | `/api/conductor/finalizar-turno/` | Solicitar/validar OTP de cierre |
| POST | `/api/conductor/cupos/` | Cambio de asientos disponibles |
| POST | `/api/telemetria/enviar/` | Telemetría GPS periódica |

---

## 8. Permisos y seguridad

- `INTERNET`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION` y `VIBRATE`
  declarados en `AndroidManifest.xml`.
- El usuario concede ubicación en tiempo de ejecución; si la niega, la app sigue
  operando con la ubicación simulada de Santiago para fines de demostración.
- El token de acceso nunca se escribe en logs (`HttpLoggingInterceptor` en nivel
  `BASIC` solo en debug).
- Sesión cifrada con `EncryptedSharedPreferences`; fallback a preferencias
  privadas si el keystore no está disponible.
- `TokenAuthenticator` evita bucles de refresh y limpia la sesión si el refresh
  falla.
- Sin claves ni secretos embebidos en el APK.

---

## 9. Validación ejecutada

```text
.\gradlew.bat :app:assembleDebug --no-daemon --console=plain
BUILD SUCCESSFUL in 4m 18s
37 actionable tasks: 37 executed
APK: app/build/outputs/apk/debug/app-debug.apk (11.5 MB)
```

Además se validó la sintaxis de todos los recursos XML con un parser XML y el
backend con `python -m pytest tests/ -q` → **64 passed**.

> La app se compiló con SDK Platform 35 instalado automáticamente por Gradle. Si
> el entorno no tiene esa plataforma, Gradle la descarga al compilar (requiere
> licencia de Android SDK aceptada).

---

## 10. Notas de diseño

- Paleta estricta: `#0B0B0B`, `#FFFFFF`, `#FFD100`. Los grises son variantes de
  transparencia del blanco, no colores nuevos.
- Tipografía Roboto (familia por defecto de Android) con pesos Black/Bold y
  tracking negativo para titulares.
- Componentes reutilizables: `ConaCard`, `ConaButton`, `ConaTextField`,
  `StatusChip`, `ErrorBanner`, `KeyValueRow`, `ConatacochMap`.
- Estados de carga con `LinearProgressIndicator` amarillo y errores en banner
  de alto contraste.
- Sin navegación profunda: el rol de la sesión decide la pantalla raíz, lo que
  reduce el estado y evita rutas inválidas.
