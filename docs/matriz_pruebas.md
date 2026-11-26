# Matriz de pruebas — CONATACOCH Fase 3

Documento de trazabilidad entre los requisitos de la Fase 3, las pruebas
automatizadas y las verificaciones manuales que respaldan las evidencias del
informe. No reemplaza a `docs/GUIA_EVIDENCIAS_Y_GIT.md`: lo complementa con el
detalle técnico de cada caso.

| Campo | Valor |
|---|---|
| Proyecto | CONATACOCH — taxi colectivo Región Metropolitana |
| Rama evaluada | `TERCERA-FASE` |
| Commit base | `5c73e91` (`avance con la conexion a base de datos`) |
| Fecha de ejecución | 2026-11-25 |
| Backend | Django 5.2.19 · DRF · SimpleJWT · PyMongo |
| Python | 3.12.10 (venv del proyecto) |
| Base relacional | MariaDB 10.4 local (`conatacoch`) / MySQL 8 en Docker |
| Base documental | MongoDB Atlas `telemetria_ubicacion.ubicaciones` |
| Web admin | HTML + CSS + JavaScript vanilla · Nginx |
| Android | Kotlin 2.x · Jetpack Compose · Material 3 · MVVM + Clean Architecture |
| Resultado automatizado | **64/64 pruebas aprobadas** |

---

## 1. Cómo reproducir la matriz

```powershell
# Backend (desde backend/)
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short

# Con SQLite temporal, sin depender de MariaDB/Atlas:
$env:DB_ENGINE="django.db.backends.sqlite3"
$env:SQLITE_PATH="./db_test_matrix.sqlite3"
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=short

# Carga de datos real (MariaDB/MySQL)
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py seed_conatacoch

# Web admin (sintaxis)
node --check web-admin/assets/app.js

# Android
cd android-app
.\gradlew.bat :app:assembleDebug
```

---

## 2. Pruebas automatizadas del backend (64)

Leyenda de estado: **APROBADO** = ejecutado en esta sesión con `pytest`;
**CUBIERTO** = misma lógica validada por la prueba indicada.

### 2.1 Autenticación, Argon2id y bloqueo (`tests/test_auth.py`)

| ID | Clase · prueba | Escenario | Resultado esperado | Estado |
|---|---|---|---|---|
| P-01 | `TestLoginArgon2id` · `test_login_exitoso_verify_argon2` | Login con credenciales válidas | HTTP 200, `access` + `refresh`, hash Argon2id verificado | APROBADO |
| P-02 | `TestLoginArgon2id` · `test_login_fallo_password_incorrecto` | Password errónea | HTTP 401, sin tokens, contador incrementado | APROBADO |
| P-03 | `TestLoginArgon2id` · `test_password_hash_no_es_texto_plano` | Inspección del hash almacenado | Prefijo `argon2$`, nunca texto plano | APROBADO |
| P-04 | `TestFuerzaBruta` · `test_bloqueo_despues_de_5_intentos` | 5 intentos fallidos | Cuenta bloqueada, HTTP 429/403 según contrato | APROBADO |
| P-05 | `TestFuerzaBruta` · `test_bloqueo_dura_15_minutos` | Ventana de bloqueo | `bloqueado_hasta` ≈ ahora + 15 min | APROBADO |
| P-06 | `TestFuerzaBruta` · `test_login_exitoso_reinicia_contador` | Login correcto tras fallos | `intentos_fallidos = 0` | APROBADO |
| P-07 | `TestFuerzaBruta` · `test_usuario_no_bloqueado_con_menos_de_5` | 4 fallos | Usuario aún habilitado | APROBADO |
| P-08 | `TestSesionUnicaOTP` · `test_conductor_no_tiene_turno_inicialmente` | Estado inicial del conductor | `en_turno = False` | APROBADO |
| P-09 | `TestSesionUnicaOTP` · `test_otp_codigo_se_genera_y_expira` | Solicitud de OTP de turno | Código de 6 dígitos + expiración | APROBADO |
| P-10 | `TestSesionUnicaOTP` · `test_otp_expira_despues_de_5_minutos` | Vigencia del OTP | Expira a los 5 min | APROBADO |
| P-11 | `TestSesionUnicaOTP` · `test_clear_token_sesion` | Cierre de turno | Token de sesión única eliminado | APROBADO |

### 2.2 Integración de flujos (`tests/test_integration.py`)

| ID | Clase · prueba | Escenario | Resultado esperado | Estado |
|---|---|---|---|---|
| P-12 | `TestLoginIntegracion` · `test_login_devuelve_access_y_refresh` | Contrato JWT | `usuario.rol`, `access_expires_in` presentes | APROBADO |
| P-13 | `TestLoginIntegracion` · `test_login_password_incorrecto_401` | Credencial inválida | HTTP 401 sin fuga de datos | APROBADO |
| P-14 | `TestLoginIntegracion` · `test_login_usuario_inexistente_401` | Email no registrado | HTTP 401 (mismo mensaje que password errónea) | APROBADO |
| P-15 | `TestRegistroConductorAdmin` · `test_admin_registra_conductor_exitoso` | Alta de conductor por ADMIN | HTTP 201, RUT/folio/patente persistidos | APROBADO |
| P-16 | `TestRegistroConductorAdmin` · `test_cliente_no_puede_registrar_conductor_403` | CLIENTE intenta alta | HTTP 403 | APROBADO |
| P-17 | `TestRegistroConductorAdmin` · `test_admin_listado_conductores_paginado` | Listado administrativo | `count`, `results`, paginación | APROBADO |
| P-18 | `TestInicioTurnoConductor` · `test_iniciar_turno_solicita_otp` | Primer POST de turno | `estado = otp_requerido` + `codigo_otp` demo | APROBADO |
| P-19 | `TestInicioTurnoConductor` · `test_iniciar_turno_con_otp_valido` | OTP correcto | `en_turno = True`, token de sesión | APROBADO |
| P-20 | `TestInicioTurnoConductor` · `test_iniciar_turno_otp_invalido_401` | OTP incorrecto | HTTP 401 | APROBADO |
| P-21 | `TestInicioTurnoConductor` · `test_sesion_unica_invalida_token_previo` | Segundo dispositivo | Token anterior invalidado | APROBADO |
| P-22 | `TestCambioCuposConductor` · `test_conductor_cambia_cupos_exitoso` | Actualización de cupos | Persistencia y reflejo en flota/ETA | APROBADO |
| P-23 | `TestCambioCuposConductor` · `test_conductor_sin_turno_no_puede_cambiar_cupos_403` | Sin turno activo | HTTP 403 | APROBADO |
| P-24 | `TestFlujoPagoQR` · `test_cliente_genera_qr_y_conductor_confirma` | Flujo QR completo | `PENDIENTE → PAGADO`, monto y folios correctos | APROBADO |
| P-25 | `TestFlujoPagoQR` · `test_cliente_no_puede_confirmar_pago_ajeno_403` | IDOR en confirmación | HTTP 403 | APROBADO |
| P-26 | `TestFlujoPagoQR` · `test_conductor_confirma_pago_de_otro_conductor_403` | Confirmación ajena | HTTP 403 | APROBADO |

### 2.3 Seguridad OWASP (`tests/test_security_owasp.py`)

| ID | Clase · prueba | Control | Resultado esperado | Estado |
|---|---|---|---|---|
| P-27 | `TestRBACRoles` · `test_cliente_no_puede_acceder_admin_403` | A01 Broken Access Control | HTTP 403 | APROBADO |
| P-28 | `TestRBACRoles` · `test_cliente_no_puede_iniciar_turno_403` | A01 | HTTP 403 | APROBADO |
| P-29 | `TestRBACRoles` · `test_conductor_no_puede_acceder_admin_tarifas_403` | A01 | HTTP 403 | APROBADO |
| P-30 | `TestRBACRoles` · `test_cliente_no_puede_enviar_telemetria_403` | A01 | HTTP 403 | APROBADO |
| P-31 | `TestRBACRoles` · `test_admin_puede_listar_conductores_200` | A01 (camino permitido) | HTTP 200 | APROBADO |
| P-32 | `TestIDOR` · `test_conductor_no_puede_ver_otro_conductor_403` | A01 IDOR | HTTP 403 | APROBADO |
| P-33 | `TestIDOR` · `test_admin_puede_ver_cualquier_conductor_200` | A01 IDOR (ADMIN) | HTTP 200 | APROBADO |
| P-34 | `TestInyeccionSQL` · `test_login_con_payload_sql_injection_no_filtra_datos` | A03 Injection | Sin bypass ni error 500 | APROBADO |
| P-35 | `TestInyeccionSQL` · `test_filtro_lineas_con_caracteres_especiales_no_causa_error_500` | A03 | Consulta parametrizada, HTTP válido | APROBADO |
| P-36 | `TestInyeccionNoSQL` · `test_telemetria_rechaza_operador_mongo_dolar` | A03 NoSQL | HTTP 400 `payload_no_permitido` | APROBADO |
| P-37 | `TestInyeccionNoSQL` · `test_telemetria_rechaza_clave_con_punto` | A03 NoSQL | HTTP 400 | APROBADO |
| P-38 | `TestGPSspoofing` · `test_telemetria_velocidad_normal_201` | A04 / anti-spoofing | HTTP 201 | APROBADO |
| P-39 | `TestGPSspoofing` · `test_telemetria_velocidad_extrema_422` | A04 | HTTP 422 (>130 km/h) | APROBADO |
| P-40 | `TestGPSspoofing` · `test_haversine_detecta_teletransporte` | A04 | Distancia/velocidad inconsistente detectada | APROBADO |
| P-41 | `TestGPSspoofing` · `test_umbral_130_kmh_es_limite` | A04 | Límite exacto respetado | APROBADO |
| P-42 | `TestExcepcionesSinStackTrace` · `test_error_interno_no_expone_stacktrace` | A05/A09 | Respuesta genérica sin trazas | APROBADO |
| P-43 | `TestExcepcionesSinStackTrace` · `test_respuesta_error_tiene_formato_estandar` | A09 | `error`, `detail`, `status_code` | APROBADO |

### 2.4 Utilidades de seguridad y dominio (`tests/test_security.py`)

| ID | Clase · prueba | Unidad validada | Estado |
|---|---|---|---|
| P-44 | `TestArgon2id` · `test_hash_y_verifica_password_correcto` | Hash/verify Argon2id | APROBADO |
| P-45 | `TestArgon2id` · `test_rechaza_password_incorrecto` | Rechazo de password | APROBADO |
| P-46 | `TestArgon2id` · `test_hash_es_deterministico_con_salt_distinto` | Salt aleatorio por hash | APROBADO |
| P-47 | `TestArgon2id` · `test_needs_rehash_detecta_parametros_antiguos` | Rehash transparente | APROBADO |
| P-48 | `TestArgon2id` · `test_identifica_hash_argon2_valido` | Detección de formato | APROBADO |
| P-49 | `TestCalculoETA` · `test_eta_conductor_cercano` | ETA con conductor próximo | APROBADO |
| P-50 | `TestCalculoETA` · `test_velocidad_calculada_delta_tiempo` | Velocidad por delta de tiempo | APROBADO |
| P-51 | `TestCalculoETA` · `test_velocidad_delta_cero_no_divide_por_cero` | División por cero | APROBADO |
| P-52 | `TestCalculoETA` · `test_velocidad_mezcla_datetime_naive_y_aware` | Zonas horarias mixtas | APROBADO |
| P-53 | `TestAntiSpoofingHaversine` · `test_velocidad_normal_no_es_sospechosa` | Haversine normal | APROBADO |
| P-54 | `TestAntiSpoofingHaversine` · `test_velocidad_supera_umbral_es_sospechosa` | Haversine sobre umbral | APROBADO |
| P-55 | `TestAntiSpoofingHaversine` · `test_distancia_santiago_providencia` | Distancia conocida (~7 km) | APROBADO |
| P-56 | `TestAntiSpoofingHaversine` · `test_distancia_misma_coordenada_es_cero` | Distancia nula | APROBADO |
| P-57 | `TestSanitizacionNoSQL` · `test_rechaza_clave_con_dolar` | Clave `$` | APROBADO |
| P-58 | `TestSanitizacionNoSQL` · `test_rechaza_clave_con_punto` | Clave con `.` | APROBADO |
| P-59 | `TestSanitizacionNoSQL` · `test_rechaza_documento_anidado_con_operador` | Operador anidado | APROBADO |
| P-60 | `TestSanitizacionNoSQL` · `test_documento_valido_pasa_sin_cambios` | Payload legítimo intacto | APROBADO |
| P-61 | `TestSanitizacionNoSQL` · `test_limpia_caracteres_control_en_strings` | Caracteres de control | APROBADO |
| P-62 | `TestUtilidadesSeguridad` · `test_hash_token_sesion_no_revela_token` | SHA-256 del token | APROBADO |
| P-63 | `TestUtilidadesSeguridad` · `test_generar_codigo_otp_es_numerico` | OTP de 6 dígitos | APROBADO |
| P-64 | `TestUtilidadesSeguridad` · `test_verificar_codigo_otp_tiempo_constante` | Comparación en tiempo constante | APROBADO |

---

## 3. Base de datos relacional (MySQL / MariaDB)

Verificación ejecutada sobre MariaDB local con las variables del archivo `env`
(`MYSQL_DATABASE=conatacoch`, `MYSQL_USER=conatacoch`,
`MYSQL_PASSWORD=conatacoch_2026`, `MYSQL_HOST=127.0.0.1`,
`MYSQL_PORT=3306`).

| ID | Verificación | Comando / método | Resultado obtenido | Estado | Evidencia |
|---|---|---|---|---|---|
| B-01 | Conexión con `.env` | `settings.DATABASES['default']` + `SELECT VERSION()` | Motor `core.db_backend`, conexión OK, versión reportada por el servidor | APROBADO | — |
| B-02 | Migraciones | `manage.py migrate --noinput` | Migraciones `0001`–`0003` aplicadas sin error | APROBADO | E-07 |
| B-03 | Seed idempotente | `manage.py seed_conatacoch` | 660 líneas actualizadas, 0 duplicadas | APROBADO | E-10 |
| B-04 | Catálogo de líneas | `LineaColectiva.objects.count()` | **660** | APROBADO | E-11 |
| B-05 | Paraderos | `Paradero.objects.count()` | **1320** (2 por recorrido) | APROBADO | E-11 |
| B-06 | Usuarios demo | `Usuario.objects.count()` | **5** (1 ADMIN, 2 CONDUCTOR, 2 CLIENTE) | APROBADO | E-10 |
| B-07 | Flota demo | `Vehiculo.objects.count()` / `Conductor.objects.count()` | **2 / 2** | APROBADO | E-10 |
| B-08 | Clientes demo | `Cliente.objects.count()` | **2** | APROBADO | E-10 |
| B-09 | Credenciales impresas | Salida del seed | `admin@`, `conductor1@`, `conductor2@`, `pasajero1@`, `pasajero2@conatacoch.cl` con sus passwords | APROBADO | E-10 |
| B-10 | Passwords operativas | `check_password()` por cada usuario demo | `True` en los 5 usuarios | APROBADO | — |
| B-11 | Esquema documentado | `docs/schema_mysql.sql` ejecutado sobre una base temporal | 7 tablas, 8 FK y todos los índices creados sin error; base temporal eliminada | APROBADO | — |
| B-12 | Diagrama ER | `docs/diagrama_er.mmd` vs `core/models.py` | 7 entidades y cardinalidades correctas | VERIFICADO | — |

Credenciales demo (las imprime `seed_conatacoch`):

| Rol | Email | Password |
|---|---|---|
| ADMIN | `admin@conatacoch.cl` | `AdminConata2026!` |
| CONDUCTOR | `conductor1@conatacoch.cl` | `Conduc2026!` |
| CONDUCTOR | `conductor2@conatacoch.cl` | `Conduc2026!` |
| CLIENTE | `pasajero1@conatacoch.cl` | `Pasajero2026!` |
| CLIENTE | `pasajero2@conatacoch.cl` | `Pasajero2026!` |

---

## 4. Base documental (MongoDB Atlas)

Índices que el backend garantiza de forma idempotente
(`core/mongo.py::ensure_indexes`, invocado en el seed, en el healthcheck y en
cada proceso que recibe telemetría):

| Índice | Clave | Opciones |
|---|---|---|
| `idx_ubicacion_2dsphere` | `ubicacion` | `2dsphere` |
| `idx_folio_timestamp` | `folio_linea` ASC, `timestamp` DESC | — |
| `idx_timestamp_ttl` | `timestamp` ASC | `expireAfterSeconds = MONGO_TTL_SECONDS` (14400) |
| `idx_vehiculo_timestamp` | `id_vehiculo` ASC, `timestamp` DESC | — |

| ID | Verificación | Método | Resultado | Estado |
|---|---|---|---|---|
| M-01 | Variables de entorno | `settings.MONGO_ATLAS_URI`, `MONGO_DB_NAME=telemetria_ubicacion`, `MONGO_COLLECTION=ubicaciones`, `MONGO_TTL_SECONDS=14400` | Leídas correctamente desde `env` | APROBADO |
| M-02 | Creación de índices | `ensure_indexes()` contra Atlas real | 4 índices creados en `telemetria_ubicacion.ubicaciones` | APROBADO |
| M-03 | Documento GeoJSON + consulta geoespacial | `insertar_ubicacion()` + `$near` (500 m) | Documento recuperado por cercanía; `coordinates = [longitud, latitud]`; documento de prueba eliminado | APROBADO |
| M-04 | Conexión Atlas real | `mongo.ping()` + `GET /api/health/` | **Ping OK (57,58 ms)**; health HTTP 200 con `mongodb.status=ok`, `mode=atlas`, `indexes=ok` | APROBADO |
| M-05 | `2dsphere`/TTL en Atlas | `index_information()` sobre el clúster real | `idx_ubicacion_2dsphere` (`2dsphere`) e `idx_timestamp_ttl` (`expireAfterSeconds=14400`) confirmados | APROBADO |

> **Resolución M-04/M-05:** tras corregir las credenciales en `env`, Atlas
> autenticó correctamente. El backend creó de forma idempotente
> `idx_ubicacion_2dsphere`, `idx_folio_timestamp`, `idx_timestamp_ttl`
> (TTL 14400 s) e `idx_vehiculo_timestamp`. Se validó además una inserción
> GeoJSON real y su recuperación con `$near`; el documento de prueba fue
> eliminado y la colección quedó en 0 documentos. Esta evidencia cubre E-12,
> E-13 y E-14.

---

## 5. API y contratos verificados

| ID | Endpoint | Verificación | Estado |
|---|---|---|---|
| A-01 | `GET /api/health/` | Reporta `mysql`, `mongodb.mode`, `database`, `collection`, `indexes` | APROBADO (código) |
| A-02 | `POST /api/auth/login/` | `access`, `refresh`, `usuario{id,rut,nombre,email,rol}`, `access_expires_in` | APROBADO |
| A-03 | `POST /api/auth/refresh/` | Renovación de access token | APROBADO |
| A-04 | `POST /api/conductores/turno/` | OTP en dos pasos (`otp_requerido` → validación) | APROBADO |
| A-05 | `POST /api/conductores/cupos/` | Cambio de cupos con turno activo | APROBADO |
| A-06 | `POST /api/telemetria/enviar/` | Ingesta GeoJSON + anti-spoofing 422 | APROBADO |
| A-07 | `POST /api/eta/calcular/` | `opciones[]` con distancia, ETA y cupos | APROBADO |
| A-08 | `POST /api/pagos/qr/` | UUID, monto, folios, estado `PENDIENTE` | APROBADO |
| A-09 | `POST /api/pagos/confirmar/` | Estado `PAGADO` solo por conductor titular | APROBADO |
| A-10 | `GET /api/flota/` | Vehículos en turno con última posición | VERIFICADO (código + build) |
| A-11 | `GET /api/admin-api/conductores/` | CRUD administrativo paginado | VERIFICADO (código + pruebas P-15/P-17) |
| A-12 | `GET/PATCH /api/admin-api/lineas/` | Tarifas y datos de recorrido | VERIFICADO (código) |
| A-13 | `GET /api/admin-api/pagos/` | Auditoría de transacciones QR | VERIFICADO (código) |

---

## 6. Web admin (JWT + Django)

| ID | Caso | Método de verificación | Resultado | Estado | Evidencia |
|---|---|---|---|---|---|
| W-01 | Login ADMIN por JWT | `api('/auth/login/')` guarda `access`/`refresh`; rol `ADMIN` habilita pestañas | Flujo implementado, endpoints existentes | VERIFICADO | E-18/E-19 |
| W-02 | Listado de conductores | `GET /conductores/?page&search` + paginación | Renderiza RUT, folio, patente | VERIFICADO | E-44 |
| W-03 | Validación RUT | Algoritmo módulo 11 en `validarRut()` | Rechaza RUT inválido antes de enviar | VERIFICADO | E-44 |
| W-04 | Validación folio | Campo obligatorio `folio_conatacoch` | Bloquea envío vacío | VERIFICADO | E-44 |
| W-05 | Validación patente | Regex `^[A-Z]{2,4}-?[0-9]{2,4}$` | Rechaza formato inválido | VERIFICADO | E-44 |
| W-06 | Alta/edición de conductor | `POST/PATCH /admin-api/conductores/` | HTTP 201/200 y refresco de listado | VERIFICADO | E-44 |
| W-07 | Líneas y tarifas | Búsqueda por folio + `PATCH /admin-api/lineas/<id>/` | Actualiza `tarifa_actual` | VERIFICADO | E-45 |
| W-08 | Auditoría QR | `GET /admin-api/pagos/` con filtros de estado | Monto, UUID, folio, fecha, estado | VERIFICADO | E-47 |
| W-09 | Paleta estricta | Revisión de `styles.css` | Solo `#0B0B0B`, `#FFFFFF`, `#FFD100` (+ transparencias derivadas) | VERIFICADO | E-38 |
| W-10 | Sintaxis JS | `node --check web-admin/assets/app.js` | Sin errores | APROBADO | — |
| W-11 | Integridad DOM | Cruce de 87 referencias `$("id")` contra 155 `id` únicos | 0 referencias huérfanas, 0 duplicados | APROBADO | — |
| W-12 | Mobile-first | Marco 420–480 px en escritorio, pantalla completa en móvil | Reglas CSS implementadas | VERIFICADO | E-36/E-37 |

Las capturas E-36…E-47 quedan pendientes de ejecución visual con el backend
levantado (`python manage.py runserver 0.0.0.0:8000`).

---

## 7. Android (Kotlin + Compose + MVVM + Clean Architecture)

| ID | Caso | Método de verificación | Resultado | Estado | Evidencia |
|---|---|---|---|---|---|
| D-01 | Compilación debug | `.\gradlew.bat :app:assembleDebug` | `BUILD SUCCESSFUL`, 37 tareas, APK ~11,5 MB | APROBADO | E-53 |
| D-02 | Recursos XML | Parseo XML de layouts, themes, strings, network config | Sin errores de sintaxis | APROBADO | — |
| D-03 | Login | `LoginViewModel` + `AuthRepositoryImpl` contra `/auth/login/` | Persistencia cifrada con `EncryptedSharedPreferences` | VERIFICADO | E-48 |
| D-04 | Ruta seleccionada | `SelectedRouteCard` + `ConatacochMap(route = state.paraderos)` | Polilínea y paraderos de la línea elegida | VERIFICADO | E-49 |
| D-05 | Vehículos en vivo | Polling de `/flota/` y marcadores OSMDroid | Posición, folio y cupos | VERIFICADO | E-49 |
| D-06 | ETA | `POST /eta/calcular/` desde `PassengerViewModel` | Opciones con minutos y cupos | VERIFICADO | E-49 |
| D-07 | Pago QR en 2 toques | `POST /pagos/qr/` → diálogo → `POST /pagos/confirmar/` | UUID, monto y confirmación | VERIFICADO | E-40 |
| D-08 | Conductor | Turno OTP, cupos, GPS periódico, alerta QR | UI de alto contraste y botones grandes | VERIFICADO | E-50/E-51/E-52 |
| D-09 | Arquitectura | Paquetes `core`, `domain`, `data`, `ui` + ViewModels | MVVM + Clean Architecture respetados | VERIFICADO | — |
| D-10 | Material 3 | `Theme.kt`, `Color.kt`, `Type.kt` | Paleta `#0B0B0B/#FFFFFF/#FFD100` | VERIFICADO | — |

Las capturas E-48…E-52 requieren emulador/dispositivo con la app instalada y el
backend accesible en `http://10.0.2.2:8000/api/`.

---

## 8. Rendimiento (Fase 2, referencia vigente)

| ID | Escenario | Muestras | Promedio | p95 | p99 | Throughput | Estado |
|---|---|---|---|---|---|---|---|
| R-01 | Telemetría GPS | 50 | 400,62 ms | 1053,99 ms | 1058,00 ms | 44,70 req/s | APROBADO |
| R-02 | Cálculo ETA | 100 | 936,55 ms | 1605,93 ms | 1662,52 ms | 55,86 req/s | APROBADO |
| R-03 | Login concurrente | 150 | — | — | — | 150 en 14,243 s | APROBADO |

Fuente: `backend/tests/bench_baseline.py` → `carga_metrics.json`.

---

## 9. Resumen de aceptación

| Área | Casos | Aprobados | Verificados | Pendientes/Bloqueados |
|---|---|---|---|---|
| Backend automatizado | 64 | 64 | 0 | 0 |
| Base relacional | 12 | 11 | 1 | 0 |
| MongoDB Atlas | 5 | 5 | 0 | 0 |
| API | 13 | 9 | 4 | 0 |
| Web admin | 12 | 2 | 10 | 0 (capturas) |
| Android | 10 | 2 | 8 | 0 (capturas) |
| Rendimiento | 3 | 3 | 0 | 0 |

**Conclusión:** la lógica de negocio, seguridad, contratos API, bases de datos y
compilación de las tres interfaces quedan aprobadas. La conexión real a
MongoDB Atlas autentica correctamente y el clúster ya contiene los índices
`2dsphere`, compuesto y TTL. Quedan pendientes únicamente las capturas de
pantalla de los flujos visuales, que se generan siguiendo
`docs/GUIA_EVIDENCIAS_Y_GIT.md`.
