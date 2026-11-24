# Guía de evidencias y Git — CONATACOCH Fase 3

Este documento resuelve dos necesidades de la entrega:

1. **Evidencias visuales:** qué captura tomar para cada `[POR COMPLETAR]` del
   informe `INFORME UNI 3 CONATACOCH.docx`, con nombre de archivo, pasos y
   criterio de aceptación.
2. **Trabajo colaborativo:** comandos Git exactos para las ramas de
   **Heiner Sepúlveda**, **Vicente Macaya** y **Félix Escobar**, incluyendo
   integración, Pull Request y publicación en GitHub.

> **Regla de oro:** una captura vale solo si se lee el dato que el informe
> afirma. No basta con la pantalla completa: debe verse el comando, la URL, el
> rol, el estado o la métrica que se está evidenciando.

---

## 1. Convenciones de captura

| Aspecto | Convención |
|---|---|
| Formato | PNG |
| Ancho mínimo | 1280 px (escritorio) / 1080 px (móvil) |
| Nombre | `faseN_YY_descripcion.png` — ejemplo: `fase2_04_login_admin.png` |
| Zona | Recortar solo la ventana relevante; evitar escritorio completo |
| Datos sensibles | Ocultar tokens completos, passwords y cadenas de conexión |
| Texto | Aumentar zoom del navegador/terminal para que el dato sea legible |
| Fecha | Mantener visible la fecha/hora del sistema cuando aporte |
| Consistencia | Mismo usuario, misma línea y mismo folio entre capturas relacionadas |

**Carpeta sugerida** (no se versiona si pesa demasiado):

```text
docs/evidencias/
├── fase1/
├── fase2/
├── fase3/
└── 4mas1/
```

Si el informe exige las imágenes embebidas, insertarlas con el pie de foto
indicado en la columna **Pie de figura**.

---

## 2. Tabla maestra de evidencias

Cada fila corresponde a un `[POR COMPLETAR]` del informe. Si el documento tiene
un marcador adicional, se agrega una fila con el mismo formato.

### 2.0 Tabla exacta para los `[POR COMPLETAR]` de `INFORME UNI 3 CONATACOCH.docx`

Esta tabla cubre exactamente los marcadores solicitados: **3.3 Figuras 1 a 4**,
**4.1**, **4.2**, **5.1**, **5.2** y **6.2**. Reemplazar cada
`[POR COMPLETAR]` / `[Insertar captura...]` por la imagen indicada y conservar
el pie de figura del informe.

| Sección | Marcador del docx | Figura / evidencia | Qué debe verse | Archivo sugerido | Cómo tomarla |
|---|---|---|---|---|---|
| **3.3** | `[POR COMPLETAR]` | **Figura 1** — Autenticación unificada | Formulario email/password, chips demo, botón Entrar y, si se quiere, el enlace “¿No tienes cuenta? Regístrate como pasajero”. Ideal: app Android y panel web lado a lado o una sola captura nítida. | `fase3_33_fig1_login.png` | Abrir la app Android sin sesión o el panel web; mostrar la pantalla de login completa con la URL de API visible. |
| **3.3** | `[POR COMPLETAR]` | **Figura 2** — Interfaz del Pasajero | Mapa en vivo con flota, trazado/ruta, tarjeta de ETA (minutos, distancia, patente, cupos) y botón **Pagar con QR**. | `fase3_33_fig2_pasajero.png` | Login `pasajero1@conatacoch.cl`; seleccionar una línea; esperar telemetría; capturar mapa + ETA + botón QR. |
| **3.3** | `[POR COMPLETAR]` | **Figura 3** — Modo Conducción | Turno activo, control `−`/`+` de cupos, estado Disponible/Lleno, GPS enviando y alerta de pago QR (visual y sonora). | `fase3_33_fig3_conductor.png` | Login `conductor1@conatacoch.cl`; iniciar turno con OTP; crear un pago desde el pasajero para que aparezca la alerta; capturar. |
| **3.3** | `[POR COMPLETAR]` | **Figura 4** — Panel Web de Administración | Panel mobile-first con flota, líneas/tarifas y auditoría de pagos QR; chip de rol ADMIN y estado de Mongo/health. | `fase3_33_fig4_admin.png` | Login `admin@conatacoch.cl` en `http://localhost:8080`; recorrer las pestañas Flota, Líneas y Pagos; capturar la vista principal. |
| **4.1** | `[Insertar captura del diagrama físico ejecutado o salida del comando SHOW TABLES; / esquema desplegado.]` | **Base de datos relacional** | Salida de `SHOW TABLES;` con las 6 tablas (`usuario`, `linea_colectiva`, `vehiculo`, `conductor`, `paradero`, `transaccion_pago`) y, opcionalmente, `SHOW INDEX` o el diagrama físico. | `fase3_41_mysql_tablas.png` | `docker compose exec db_mysql mysql -uconatacoch -p conatacoch -e "SHOW TABLES;"` (ocultar password). |
| **4.2** | `[Insertar captura de la interfaz web de MongoDB Atlas mostrando el clúster activo y documentos reales insertados.]` | **Base de datos NoSQL en la nube** | Clúster de Atlas activo + base `telemetria_ubicacion`, colección `ubicaciones` y un documento GeoJSON con `ubicacion.coordinates`, `velocidad_kmh`, `timestamp` e `id_vehiculo`. | `fase3_42_mongodb_atlas.png` | Atlas → Browse Collections → `telemetria_ubicacion.ubicaciones`; enviar telemetría antes para que exista un documento real. |
| **5.1** | `[Insertar 2 o 3 fragmentos breves o capturas reales de su código fuente mostrando el middleware RBAC/JWT, el hashing Argon2id y la validación de coordenadas.]` | **Patrones de seguridad en código** | Tres recuadros legibles: (a) `permissions.py` / JWT y RBAC, (b) `security.py` con Argon2id, (c) `security.py` con Haversine/`es_velocidad_sospechosa` y HTTP 422. | `fase3_51_codigo_rbac_argon2.png` y `fase3_51_codigo_antispuf.png` | Abrir los archivos en el IDE, resaltar las líneas y capturar; ocultar claves y rutas absolutas. |
| **5.2** | `[Insertar captura del gráfico de contribuciones o historial de commits/ramas en GitHub.]` | **Trabajo colaborativo Git** | Gráfico de contribuciones de los tres integrantes o `git log --oneline --graph --all` con ramas `feature/*` y commits de **Heiner Sepúlveda**, **Vicente Macaya** y **Félix Escobar**. | `fase3_52_git_historial.png` | Ejecutar `git log --oneline --graph --all -30` y/o abrir GitHub → Insights → Contributors. |
| **6.2** | `[Insertar captura de la terminal mostrando docker-compose up / contenedores corriendo sin errores y las variables de entorno configuradas (ocultando contraseñas reales).]` | **Guía de instalación y despliegue** | Terminal con `docker compose ... up -d --build`, luego `docker compose ps` con `db_mysql`, `backend`, `web_admin` y `mongo_local` en `Up/healthy`; `.env` visible con secretos tapados. | `fase3_62_docker_up.png` | Ejecutar los comandos de la sección 3.1; capturar terminal y una segunda ventana con `.env` censurado. |

> **Regla para 5.1:** si el informe solo admite una imagen, unir los tres
> recuadros en un collage vertical y usar `fase3_51_codigo_seguridad.png`.
> **Regla para 3.3:** las cuatro figuras deben ser del software real, no del
> prototipo estático; si una pantalla no cabe, usar scroll y una segunda captura
> con el sufijo `_b`.

### 2.1 Portada, resumen y contexto

| ID | Sección del informe | Captura a tomar | Qué debe verse | Pasos | Archivo | Pie de figura |
|---|---|---|---|---|---|---|
| E-01 | Portada / identificación | Repositorio abierto en GitHub | Nombre `PROYECTO-CONATACOCH`, rama `main`, último commit y autores | Abrir `https://github.com/NiightSD/PROYECTO-CONATACOCH` | `fase3_01_repo_github.png` | Repositorio oficial del proyecto |
| E-02 | Resumen ejecutivo | Árbol de carpetas raíz | `backend/`, `web-admin/`, `android-app/`, `docs/`, `README.md` | Abrir el proyecto en VS Code / Explorador | `fase3_02_arbol_monorepo.png` | Estructura del monorepo |
| E-03 | Stack tecnológico | `README.md` sección 2 | Tabla de stack completa | Abrir README renderizado | `fase3_03_stack.png` | Stack tecnológico documentado |
| E-04 | Estado de fases | `README.md` sección 1 | Tabla Fase 1/2/3 con estados ✅ | Abrir README renderizado | `fase3_04_fases.png` | Estado de las tres fases |

### 2.2 Fase 1 — Infraestructura, datos y Docker

| ID | Sección del informe | Captura a tomar | Qué debe verse | Pasos | Archivo | Pie de figura |
|---|---|---|---|---|---|---|
| E-05 | Entorno Docker | `docker compose ps` | 4 servicios `Up`/`healthy`: `db_mysql`, `backend`, `web_admin`, `mongo_local` | `docker compose --profile mongo-local up -d --build` y luego `docker compose ps` | `fase1_05_compose_ps.png` | Servicios activos de la plataforma |
| E-06 | Dockerfiles / Compose | `docker-compose.yml` en el editor | Servicios, healthchecks, volúmenes y red | Abrir el archivo | `fase1_06_compose_yml.png` | Orquestación de contenedores |
| E-07 | Modelo relacional | Diagrama o `SHOW TABLES;` | 6 tablas: `usuario`, `linea_colectiva`, `vehiculo`, `conductor`, `paradero`, `transaccion_pago` | `docker compose exec db_mysql mysql -uconatacoch -p conatacoch -e "SHOW TABLES;"` | `fase1_07_tablas_mysql.png` | Modelo relacional en MySQL 8 |
| E-08 | Normalización 3FN | `README.md` sección 7.1 | Justificación 1FN/2FN/3FN y claves | Abrir README | `fase1_08_3fn.png` | Justificación de normalización |
| E-09 | Índices | `SHOW INDEX FROM linea_colectiva;` | Índices B-Tree y UNIQUE | Ejecutar en MySQL | `fase1_09_indices.png` | Índices y restricciones |
| E-10 | Seed oficial | Salida de `seed_conatacoch` | 660 líneas, 1.320 paraderos, 5 usuarios, 2 vehículos, 2 conductores | `docker compose exec backend python manage.py seed_conatacoch` | `fase1_10_seed.png` | Carga inicial idempotente |
| E-11 | Conteo de datos | `SELECT COUNT(*)` | 660 líneas, 396 folios, 48 comunas | Ejecutar consultas del README | `fase1_11_conteos.png` | Datos oficiales cargados |
| E-12 | MongoDB Atlas | Atlas UI → colección `ubicaciones` | Documento GeoJSON con `coordinates`, `timestamp`, `id_vehiculo` | Abrir Atlas → Browse Collections | `fase1_12_mongo_documento.png` | Telemetría GeoJSON en MongoDB |
| E-13 | Índices Mongo | Atlas UI → Indexes | `2dsphere`, `folio+timestamp`, TTL 14400 s, `vehiculo+timestamp` | Atlas → Indexes | `fase1_13_mongo_indices.png` | Índices geoespaciales y TTL |
| E-14 | Health | Navegador en `/api/health/` | `status: ok`, latencias MySQL y Mongo | Abrir `http://localhost:8080/api/health/` | `fase1_14_health.png` | Readiness de la plataforma |
| E-15 | Swagger | `/api/docs/` | Listado de endpoints y esquema | Abrir `http://localhost:8080/api/docs/` | `fase1_15_swagger.png` | Documentación OpenAPI 3 |
| E-16 | Django Admin | `/admin/` autenticado | Login y listados de entidades | Abrir `http://localhost:8080/admin/` | `fase1_16_django_admin.png` | Administración nativa de Django |
| E-17 | Panel base | `http://localhost:8080` | Vista inicial del panel | Abrir el panel | `fase1_17_panel_base.png` | Panel web servido por Nginx |

### 2.3 Fase 2 — Seguridad, tiempo real y pagos

| ID | Sección del informe | Captura a tomar | Qué debe verse | Pasos | Archivo | Pie de figura |
|---|---|---|---|---|---|---|
| E-18 | Login unificado | Pantalla de login del panel | Formulario email/password y mensaje de rol | Abrir panel sin sesión | `fase2_18_login.png` | Acceso unificado |
| E-19 | Login API | Postman/curl a `/api/auth/login/` | Request y response con `access`, `refresh`, `usuario.rol` | Ejecutar el ejemplo del README | `fase2_19_login_api.png` | Respuesta JWT del login |
| E-20 | Detección de rol | Panel tras login como conductor | Vista de conductor y chip de rol | Login con `conductor1@conatacoch.cl` | `fase2_20_rol_conductor.png` | Detección automática de rol |
| E-21 | RBAC 401 | `curl` sin token a `/api/conductores/` | HTTP 401 | Ejecutar sin `Authorization` | `fase2_21_rbac_401.png` | Rechazo de acceso sin JWT |
| E-22 | RBAC 403 | Token de cliente contra endpoint admin | HTTP 403 | Login cliente + llamada admin | `fase2_22_rbac_403.png` | Rechazo por rol insuficiente |
| E-23 | Bloqueo fuerza bruta | 5 logins fallidos | Mensaje de bloqueo 15 min | Repetir password incorrecta 5 veces | `fase2_23_bloqueo.png` | Protección anti-fuerza bruta |
| E-24 | OTP de turno | Diálogo OTP del conductor | Código demo, expiración y campo de 6 dígitos | Iniciar turno en panel/app | `fase2_24_otp_turno.png` | Turno protegido con OTP |
| E-25 | Telemetría GPS | Request a `/api/telemetria/enviar/` | Payload y HTTP 201 | Enviar desde la app o curl | `fase2_25_telemetria.png` | Ingesta GPS autenticada |
| E-26 | Anti-spoofing | Request con salto imposible | HTTP 422 y motivo | Enviar coordenadas muy distantes en < 1 s | `fase2_26_antispuf.png` | Rechazo de telemetría falsa |
| E-27 | ETA | Respuesta de `/api/eta/calcular/` | `opciones[]` con `distancia_km`, `eta_minutos`, `cupos` | Ejecutar con línea y coordenadas | `fase2_27_eta.png` | Cálculo de ETA y opciones |
| E-28 | Pago QR — creación | Response de `/api/pagos/qr/` | `codigo_qr_uuid`, `estado: PENDIENTE`, monto | Crear pago desde el panel | `fase2_28_pago_creado.png` | Generación del pago QR |
| E-29 | Pago QR — alerta | Pantalla del conductor con alerta | Monto grande, botón confirmar, aviso sonoro | Crear pago y esperar polling | `fase2_29_alerta_pago.png` | Alerta de pago en el conductor |
| E-30 | Pago QR — confirmación | Response de `/api/pagos/confirmar/` | `estado: PAGADO` | Confirmar desde conductor | `fase2_30_pago_confirmado.png` | Confirmación del pago |
| E-31 | Pago QR — auditoría | Vista admin de pagos | Listado con UUID, monto, estado, fecha | Abrir pestaña Pagos del panel | `fase2_31_auditoria_pagos.png` | Auditoría de transacciones |
| E-32 | Suite de pruebas | Terminal con `pytest` | `64 passed` | `cd backend && python -m pytest tests/ -q` | `fase2_32_pytest.png` | Suite automatizada aprobada |
| E-33 | Carga GPS | Tabla/resumen de `bench_baseline` | 50/50, `44.70 req/s`, p95, p99 | Ejecutar benchmark | `fase2_33_carga_gps.png` | Resultados de carga GPS |
| E-34 | Carga ETA | Tabla/resumen de `bench_baseline` | 100/100, `55.86 req/s`, p95, p99 | Ejecutar benchmark | `fase2_34_carga_eta.png` | Resultados de carga ETA |
| E-35 | Logins concurrentes | Salida del benchmark | 150 logins en 14.243 s | Ejecutar benchmark | `fase2_35_logins.png` | Autenticación concurrente |

### 2.4 Fase 3 — Interfaces y operación

| ID | Sección del informe | Captura a tomar | Qué debe verse | Pasos | Archivo | Pie de figura |
|---|---|---|---|---|---|---|
| E-36 | Panel mobile-first escritorio | Panel centrado como teléfono | Marco de 420–480 px, paleta negro/blanco/amarillo | Abrir panel en escritorio | `fase3_36_panel_desktop.png` | Vista mobile-first en escritorio |
| E-37 | Panel mobile-first móvil | Panel a pantalla completa | Sin marco, navegación inferior, botones táctiles | Abrir con DevTools → dispositivo | `fase3_37_panel_movil.png` | Vista a pantalla completa en móvil |
| E-38 | Paleta estricta | DevTools → estilos | Variables `#0B0B0B`, `#FFFFFF`, `#FFD100` | Inspeccionar `styles.css` | `fase3_38_paleta.png` | Paleta oficial de marca |
| E-39 | Mapa pasajero | Vista Pasajero con Leaflet | Marcadores de flota, ETA y cupos | Login pasajero → seleccionar línea | `fase3_39_mapa_pasajero.png` | Mapa y flota en vivo |
| E-40 | Pago QR pasajero | Diálogo QR del panel | QR renderizado, monto y estado | Botón Pagar con QR | `fase3_40_qr_pasajero.png` | Pago QR en dos toques |
| E-41 | Conductor oscuro | Vista Conductor | Alto contraste, botones grandes, estado de turno | Login conductor | `fase3_41_conductor.png` | Modo conducción de alto contraste |
| E-42 | Cambio de asientos | Tarjeta de cupos | Botones `−`/`+`, Disponible/Lleno, cupos | Cambiar cupos en panel | `fase3_42_asientos.png` | Cambio rápido de cupos |
| E-43 | GPS periódico | Tarjeta GPS del conductor | Estado "Enviando", coordenadas y frecuencia | Activar GPS con turno activo | `fase3_43_gps.png` | Emisor GPS periódico |
| E-44 | CRUD conductores | Pestaña Conductores | Formulario completo y listado | Abrir pestaña Conductores | `fase3_44_crud_conductores.png` | CRUD de conductores |
| E-45 | CRUD líneas | Pestaña Líneas | Búsqueda por folio, tarifa y edición | Abrir pestaña Líneas | `fase3_45_crud_lineas.png` | Gestión de líneas y tarifas |
| E-46 | Flota admin | Pestaña Flota | Mapa y listado con patente, folio, cupos | Abrir pestaña Flota | `fase3_46_flota_admin.png` | Flota en vivo para administración |
| E-47 | Auditoría QR | Pestaña Pagos | Filtros por estado y detalle | Abrir pestaña Pagos | `fase3_47_auditoria.png` | Auditoría de pagos QR |
| E-48 | Android — login | Emulador, pantalla de login | Logo, campos, chips demo y URL de API | Ejecutar app | `fase3_48_android_login.png` | Login de la app Android |
| E-49 | Android — pasajero | Mapa OSMDroid + ETA | Marcadores, ETA y botón QR | Login pasajero en app | `fase3_49_android_pasajero.png` | Pantalla de pasajero |
| E-50 | Android — conductor | Pantalla oscura | Botones grandes, cupos y GPS | Login conductor en app | `fase3_50_android_conductor.png` | Pantalla de conductor |
| E-51 | Android — OTP | Diálogo OTP | Código demo y campo de 6 dígitos | Iniciar turno en app | `fase3_51_android_otp.png` | Turno con OTP en Android |
| E-52 | Android — alerta QR | Diálogo amarillo de pago | Monto y botón confirmar | Crear pago desde el panel | `fase3_52_android_alerta.png` | Alerta sonora de pago QR |
| E-53 | Android — build | Terminal con Gradle | `BUILD SUCCESSFUL` y ruta del APK | `.\gradlew.bat :app:assembleDebug` | `fase3_53_android_build.png` | Compilación de la app |
| E-54 | Android — estructura | Árbol `app/src/main/java` | Paquetes `core`, `domain`, `data`, `ui` | Abrir en Android Studio | `fase3_54_android_arquitectura.png` | MVVM + Clean Architecture |
| E-55 | Endpoints Fase 3 | Swagger filtrado | Flota, perfil, cierre de turno, CRUD admin | Abrir `/api/docs/` | `fase3_55_swagger_fase3.png` | Endpoints aditivos de Fase 3 |

### 2.5 Arquitectura 4+1

| ID | Sección del informe | Captura a tomar | Qué debe verse | Pasos | Archivo | Pie de figura |
|---|---|---|---|---|---|---|
| E-56 | Vista Lógica | Diagrama Mermaid renderizado | Capas, módulos y dependencias | Abrir README sección 6.1 | `fase3_56_logica.png` | Vista Lógica |
| E-57 | Vista de Procesos | Diagramas de secuencia | Arranque, request y pago QR | README sección 6.2 | `fase3_57_procesos.png` | Vista de Procesos |
| E-58 | Vista de Desarrollo | Tabla de responsabilidades | Áreas, responsables y convenciones | README sección 6.3 | `fase3_58_desarrollo.png` | Vista de Desarrollo |
| E-59 | Vista Física | Diagrama de despliegue | Nginx, backend, MySQL, Mongo, app | README sección 6.4 | `fase3_59_fisica.png` | Vista Física |
| E-60 | Vista de Escenarios | Tabla E1–E8 | Actores, flujos y componentes | README sección 6.5 | `fase3_60_escenarios.png` | Vista de Escenarios |

### 2.6 Conclusiones y trabajo colaborativo

| ID | Sección del informe | Captura a tomar | Qué debe verse | Pasos | Archivo | Pie de figura |
|---|---|---|---|---|---|---|
| E-61 | Conclusiones | README sección 16 | Tabla de trazabilidad con la rúbrica | Abrir README | `fase3_61_trazabilidad.png` | Trazabilidad con la rúbrica |
| E-62 | Git — ramas | `git branch -a` | Ramas locales y remotas por integrante | Ejecutar en el repo | `fase3_62_ramas.png` | Ramas del equipo |
| E-63 | Git — historial | `git log --oneline --graph` | Commits por fase y autor | Ejecutar en el repo | `fase3_63_historial.png` | Historial de commits |
| E-64 | Git — Pull Request | PR en GitHub | Título, descripción, checks y revisores | Abrir el PR | `fase3_64_pull_request.png` | Integración mediante Pull Request |
| E-65 | GitHub — release/tag | Página de releases o tags | Versión `v3.0.0` | Crear tag y release | `fase3_65_release.png` | Versión final publicada |

---

## 3. Cómo reproducir cada evidencia

### 3.1 Levantar la plataforma

```bash
cp .env.example .env
# editar SECRET_KEY, JWT_SECRET, MYSQL_PASSWORD
docker compose --profile mongo-local up -d --build
docker compose ps
```

Esperar a que `backend` quede `healthy` y abrir
<http://localhost:8080>.

### 3.2 Ejecutar la suite

```bash
docker compose exec backend python -m pytest tests/ -q --tb=short
# o local:
cd backend
python -m pytest tests/ -q --tb=short
```

### 3.3 Ejecutar pruebas de carga

```bash
cd backend
python manage.py seed_carga --conductores 50
python tests/bench_baseline.py
```

El resultado se escribe en `carga_metrics.json`. Capturar la tabla resumen.

### 3.4 Compilar la app Android

```powershell
cd android-app
.\gradlew.bat :app:assembleDebug --no-daemon --console=plain
```

Capturar `BUILD SUCCESSFUL` y la ruta
`app/build/outputs/apk/debug/app-debug.apk`.

### 3.5 Verificar el panel

```bash
node --check web-admin/assets/app.js
```

Abrir el panel en escritorio y en modo dispositivo (DevTools → Toggle device
toolbar → iPhone 14 Pro / Pixel 7).

---

## 4. Estado actual del repositorio

```text
Repositorio : https://github.com/NiightSD/PROYECTO-CONATACOCH.git
Rama actual : SEGUNDA-FASE
Ramas       : main, SEGUNDA-FASE
Remoto      : origin (GitHub)
```

**Trabajo de Fase 3 pendiente de commit** (no se commitea sin autorización):

```text
M  backend/core/urls.py
M  web-admin/index.html
M  web-admin/assets/styles.css
M  web-admin/assets/app.js
?? backend/core/serializers_fase3.py
?? backend/core/views_fase3.py
?? web-admin/assets/recorridos_conatacoch.json
?? android-app/  (código fuente, Gradle, recursos)
?? docs/GUIA_EVIDENCIAS_Y_GIT.md
```

> `android-app/app/build/`, `android-app/.gradle/`, `android-app/local.properties`
> y `*.log` están excluidos por `.gitignore`. **Nunca** commitear el APK ni
> `local.properties`.

---

## 5. Git por integrante

### 5.1 Configuración inicial (cada integrante, una vez)

```bash
git config --global user.name "Nombre Apellido"
git config --global user.email "correo@ejemplo.cl"
git config --global init.defaultBranch main
git config --global pull.rebase true
```

Verificar:

```bash
git config --global --list
```

**Convención de ramas**

```text
main                         -> entrega estable
feature/heiner-backend       -> Heiner Sepúlveda
feature/vicente-web          -> Vicente Macaya
feature/felix-android-docs   -> Félix Escobar
```

**Convención de commits** (Conventional Commits, en español o inglés corto):

```text
feat(fase3): ...
fix(fase3): ...
docs(fase3): ...
test(fase2): ...
chore(repo): ...
```

### 5.2 Heiner Sepúlveda — backend y seguridad

**Alcance:** `backend/core/views_fase3.py`, `serializers_fase3.py`,
`urls.py`, pruebas, endpoints de flota/perfil/cierre de turno y CRUD admin.

```bash
# 1. Actualizar main
git checkout main
git pull origin main

# 2. Crear su rama
git checkout -b feature/heiner-backend

# 3. Revisar cambios
git status
git diff -- backend/core/urls.py

# 4. Agregar solo backend
git add backend/core/views_fase3.py
git add backend/core/serializers_fase3.py
git add backend/core/urls.py

# 5. Commit
git commit -m "feat(fase3): endpoints de flota, perfil y CRUD administrativo"

# 6. Validar antes de subir
cd backend
python manage.py check
python -m pytest tests/ -q --tb=short
cd ..

# 7. Publicar
git push -u origin feature/heiner-backend
```

**Evidencias que aporta:** E-05 a E-17, E-18 a E-35, E-55, E-63.

### 5.3 Vicente Macaya — panel web mobile-first

**Alcance:** `web-admin/index.html`, `web-admin/assets/styles.css`,
`web-admin/assets/app.js`, `web-admin/assets/recorridos_conatacoch.json`.

```bash
# 1. Actualizar main
git checkout main
git pull origin main

# 2. Crear su rama
git checkout -b feature/vicente-web

# 3. Validar sintaxis
node --check web-admin/assets/app.js

# 4. Agregar solo el panel
git add web-admin/index.html
git add web-admin/assets/styles.css
git add web-admin/assets/app.js
git add web-admin/assets/recorridos_conatacoch.json

# 5. Commit
git commit -m "feat(fase3): panel web mobile-first con roles, mapa y auditoria QR"

# 6. Publicar
git push -u origin feature/vicente-web
```

**Evidencias que aporta:** E-36 a E-47, E-02, E-60.

> Si el catálogo JSON se considera un artefacto pesado, verificar su tamaño
> (286 KB) y confirmar que no excede el límite del repositorio. Está justificado
> porque el panel funciona sin backend para la búsqueda inicial.

### 5.4 Félix Escobar — app Android y documentación

**Alcance:** `android-app/`, `README.md`, `docs/GUIA_EVIDENCIAS_Y_GIT.md`.

```bash
# 1. Actualizar main
git checkout main
git pull origin main

# 2. Crear su rama
git checkout -b feature/felix-android-docs

# 3. Verificar que no se cuele el build
git status --short --untracked-files=all | Select-String "android-app"

# 4. Agregar configuración y código (NO build/ ni local.properties)
git add android-app/settings.gradle.kts
git add android-app/build.gradle.kts
git add android-app/gradle.properties
git add android-app/gradle/wrapper/gradle-wrapper.properties
git add android-app/gradle/wrapper/gradle-wrapper.jar
git add android-app/gradlew
git add android-app/gradlew.bat
git add android-app/app/build.gradle.kts
git add android-app/app/proguard-rules.pro
git add android-app/app/src
git add android-app/README.md

# 5. Documentación
git add README.md
git add docs/GUIA_EVIDENCIAS_Y_GIT.md

# 6. Compilar antes de subir
cd android-app
.\gradlew.bat :app:assembleDebug --no-daemon --console=plain
cd ..

# 7. Commit
git commit -m "feat(fase3): app Android Kotlin/MVVM y documentacion de evidencias"

# 8. Publicar
git push -u origin feature/felix-android-docs
```

**Evidencias que aporta:** E-48 a E-54, E-01, E-03, E-04, E-56 a E-65.

> En Linux/macOS usar `./gradlew :app:assembleDebug`. En Windows
> `.\gradlew.bat`. El wrapper JAR debe quedar versionado; el SDK y
> `local.properties` no.

### 5.5 Integración de las tres ramas

**Opción A — Pull Requests en GitHub (recomendada)**

1. Cada integrante abre un PR de su rama hacia `main`.
2. Título: `Fase 3 — <área>`.
3. Descripción con:
   - Qué cambia.
   - Cómo se probó (`pytest`, `node --check`, `assembleDebug`).
   - Capturas principales.
4. Revisor: otro integrante.
5. Merge con **Squash and merge** o **Merge commit** (elegir una y mantenerla).

**Opción B — integración local secuencial**

```bash
git checkout main
git pull origin main

git merge --no-ff feature/heiner-backend -m "merge: backend fase 3"
git merge --no-ff feature/vicente-web -m "merge: panel web fase 3"
git merge --no-ff feature/felix-android-docs -m "merge: android y docs fase 3"

git push origin main
```

Si hay conflictos:

```bash
git status
# resolver archivos marcados
git add <archivo>
git commit
```

**Verificación final en `main`**

```bash
git checkout main
git pull origin main

cd backend
python manage.py check
python -m pytest tests/ -q --tb=short
cd ..

node --check web-admin/assets/app.js

cd android-app
.\gradlew.bat :app:assembleDebug --no-daemon --console=plain
cd ..

git log --oneline --graph -10
git status
```

### 5.6 Publicación en GitHub

```bash
# Verificar remoto
git remote -v

# Subir main
git push origin main

# Etiqueta de entrega
git tag -a v3.0.0 -m "CONATACOCH Fase 3 - entrega final"
git push origin v3.0.0
```

Crear el release en GitHub:

1. **Releases → Draft a new release**.
2. Tag `v3.0.0`, target `main`.
3. Título: `CONATACOCH Fase 3 — Plataforma completa`.
4. Adjuntar `app-debug.apk` si el curso lo permite (el APK no se versiona).
5. Publicar.

**Si `gh` CLI está disponible:**

```bash
gh auth login
gh pr create --base main --head feature/heiner-backend \
  --title "Fase 3 — Backend" --body "Endpoints de flota, perfil y CRUD admin."
gh release create v3.0.0 --title "CONATACOCH Fase 3" --notes "Entrega final"
```

> En este entorno `gh` no está instalado; usar la interfaz web de GitHub.

---

## 6. Checklist final de entrega

### Código

- [ ] `backend/core/urls.py` incluye rutas Fase 3.
- [ ] `python manage.py check` sin errores.
- [ ] `python -m pytest tests/ -q` → `64 passed`.
- [ ] `node --check web-admin/assets/app.js` → OK.
- [ ] `.\gradlew.bat :app:assembleDebug` → `BUILD SUCCESSFUL`.
- [ ] `.gitignore` excluye `build/`, `.gradle/`, `local.properties`, `*.log`.
- [ ] No hay secretos ni tokens en el repositorio.

### Documentación

- [ ] `README.md` con fases, stack, 4+1, endpoints, seguridad y métricas.
- [ ] `android-app/README.md` con build y ejecución.
- [ ] `docs/GUIA_EVIDENCIAS_Y_GIT.md` (este documento).
- [ ] Tabla de capturas completa (E-01 a E-65).
- [ ] Métricas reales: GPS `44.70 req/s`, ETA `55.86 req/s`, 64 pruebas.

### Evidencias

- [ ] Capturas renombradas según la convención.
- [ ] Cada `[POR COMPLETAR]` del docx tiene su imagen.
- [ ] Las capturas muestran datos legibles (no solo ventanas vacías).
- [ ] Tokens y passwords ocultos.

### Git

- [ ] Tres ramas `feature/*` publicadas.
- [ ] Tres Pull Requests revisados y mergeados.
- [ ] `main` actualizado y compilando.
- [ ] Tag `v3.0.0` creado.
- [ ] Historial con autores de los tres integrantes.

---

## 7. Anexo — correspondencia rápida informe ↔ evidencia

| Bloque del informe | IDs de evidencia |
|---|---|
| Portada y resumen | E-01 a E-04 |
| Fase 1 — Docker y datos | E-05 a E-17 |
| Fase 2 — Seguridad y tiempo real | E-18 a E-35 |
| Fase 3 — Web y Android | E-36 a E-55 |
| Arquitectura 4+1 | E-56 a E-60 |
| Conclusiones y Git | E-61 a E-65 |

Si el docx agrega un `[POR COMPLETAR]` nuevo, duplicar una fila, asignar el
siguiente ID (`E-66`, `E-67`, …) y mantener el mismo formato de columnas.
