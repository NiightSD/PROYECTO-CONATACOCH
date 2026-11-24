# CONATACOCH — Plataforma de Taxis y Colectivos de Chile

> **Fase 3 de 3 — Plataforma completa:** backend seguro, panel web mobile-first,
> app Android nativa y pagos QR en tiempo real.
> Monorepo reproducible con Docker, persistencia poliglota y arquitectura 4+1.

![Fase](https://img.shields.io/badge/fase-3%20de%203-FFD100)
![Django](https://img.shields.io/badge/Django-5.2-0C4B33)
![DRF](https://img.shields.io/badge/DRF-3.18-A30000)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Kotlin](https://img.shields.io/badge/Kotlin-2.0.21-7F52FF)
![Compose](https://img.shields.io/badge/Jetpack-Compose-4285F4)

---

## Tabla de contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura del monorepo](#3-estructura-del-monorepo)
4. [Inicio rápido](#4-inicio-rápido)
5. [Credenciales de prueba](#5-credenciales-de-prueba)
6. [Arquitectura — Modelo 4+1](#6-arquitectura--modelo-41)
7. [Bases de datos](#7-bases-de-datos)
8. [Carga inicial idempotente](#8-carga-inicial-idempotente)
9. [Escalabilidad horizontal](#9-escalabilidad-horizontal)
10. [Seguridad](#10-seguridad)
11. [API REST](#11-api-rest)
12. [Panel web mobile-first](#12-panel-web-mobile-first)
13. [App Android](#13-app-android)
14. [Pruebas, métricas y validación](#14-pruebas-métricas-y-validación)
15. [Operación y troubleshooting](#15-operación-y-troubleshooting)
16. [Trazabilidad con la rúbrica](#16-trazabilidad-con-la-rúbrica)
17. [Evidencias y Git](#17-evidencias-y-git)

---

## 1. Resumen ejecutivo

CONATACOCH es la plataforma del gremio de **taxis y colectivos de Chile**. El
proyecto se entregó en tres fases incrementales sobre el mismo monorepo:

| Fase | Alcance | Estado |
|---|---|---|
| **Fase 1** | Infraestructura Docker, modelo 3FN, seed oficial, MongoDB Atlas, panel base, documentación 4+1 | ✅ |
| **Fase 2** | Login Argon2id + JWT, RBAC, telemetría GPS anti-spoofing, turnos OTP, ETA, pagos QR, pruebas de carga | ✅ |
| **Fase 3** | Panel web mobile-first, app Android Kotlin/MVVM, endpoints de flota/perfil/cierre de turno, CRUD admin completo, guía de evidencias | ✅ |

**Entregables verificables**

| Componente | Estado | Evidencia |
|---|---|---|
| Backend Django 5 + DRF | ✅ | `backend/`, `python manage.py check`, 64 pruebas |
| MySQL 8.0 normalizado en 3FN | ✅ | 6 entidades, índices B-Tree, `PROTECT` |
| MongoDB Atlas `telemetria_ubicacion` | ✅ | Índices `2dsphere`, compuesto y TTL 4 h |
| Panel web mobile-first | ✅ | `web-admin/` con paleta `#0B0B0B` / `#FFFFFF` / `#FFD100` |
| App Android nativa | ✅ | `android-app/`, `assembleDebug` → `BUILD SUCCESSFUL` |
| Pagos QR de punta a punta | ✅ | Crear → alertar al conductor → confirmar → consultar estado |
| Pruebas automatizadas | ✅ | `64 passed` con `pytest` |
| Pruebas de carga | ✅ | GPS 50 req · `44.70 req/s`; ETA 100 req · `55.86 req/s` |
| Documentación y evidencias | ✅ | este README + `docs/` + `docs/GUIA_EVIDENCIAS_Y_GIT.md` |

**Datos oficiales cargados:** 660 itinerarios de la Región Metropolitana,
396 folios únicos, 48 comunas, 617 combinaciones `(folio, nombre_recorrido)` y
660 combinaciones `(folio, nombre_recorrido, tipo_trazado)`.

---

## 2. Stack tecnológico

| Capa | Tecnología | Rol |
|---|---|---|
| Runtime | **Python 3.12** (`python:3.12-slim`) | Base reproducible de la imagen |
| API | **Django 5.2 + Django REST Framework 3.18** | Dominio y API REST |
| Contratos | **drf-spectacular + sidecar** | OpenAPI 3 y Swagger UI local |
| Auth | **SimpleJWT + Argon2id** | Access/refresh tokens y hash de passwords |
| Driver SQL | **PyMySQL** (puro Python) | Sin toolchain nativo en la imagen |
| RDBMS | **MySQL 8.0** | Consistencia transaccional (3FN) |
| NoSQL | **MongoDB Atlas / 8.0 local** | Telemetría GeoJSON de alta escritura |
| Driver NoSQL | **PyMongo** con `maxPoolSize` | Pool de conexiones documental |
| Servidor | **Gunicorn `gthread`** | Workers + threads, stateless |
| Web | **Nginx 1.27 Alpine** | Estáticos, reverse proxy, DNS dinámico |
| Cifrado | **cryptography (Fernet)** | Secretos OTP reversibles |
| Web admin | **HTML5 + CSS3 + JavaScript ES2020** | SPA mobile-first sin build step |
| Mapas web | **Leaflet + OpenStreetMap/Carto** | Mapa de flota y ETA |
| QR web | **qrcode-generator (CDN)** | Render del código de pago |
| Mobile | **Kotlin 2.0.21 + Jetpack Compose + Material 3** | App Android nativa |
| Red mobile | **Retrofit 2.11 + OkHttp 4.12 + Gson** | Cliente REST con JWT |
| Mapas mobile | **OSMDroid 6.1.20 + Esri Dark Gray** | Mapa oscuro sin Google Play Services ni API key |
| QR mobile | **ZXing core 3.5.3** | Render local del QR |
| Contenedores | **Docker + Compose v2** | Orquestación local y despliegue |

---

## 3. Estructura del monorepo

```text
PROYECTO-CONATACOCH/
├── docker-compose.yml               # Servicios de producción
├── docker-compose.dev.yml           # Override local (expone :8000 y DEBUG=True)
├── .env.example                     # Contrato de configuración (12-factor)
├── recorridos_conatacoch_taxi_colectivo_2.json   # Dataset oficial (660 filas)
├── README.md                        # Este documento
│
├── backend/
│   ├── Dockerfile / entrypoint.sh
│   ├── requirements.txt / manage.py
│   ├── conatacoch/
│   │   ├── settings.py              # 12-factor, JWT, pools, Mongo, logging
│   │   ├── urls.py                  # /api/docs/, /admin/
│   │   └── wsgi.py / asgi.py
│   ├── core/
│   │   ├── models.py                # 6 entidades 3FN + índices + constraints
│   │   ├── serializers.py           # Serializers de lectura
│   │   ├── serializers_fase2.py     # Login, telemetría, pagos, ETA
│   │   ├── serializers_fase3.py     # CRUD admin completo y upsert de líneas
│   │   ├── views.py                 # Salud, métricas, viewsets read-only
│   │   ├── views_fase2.py           # Auth, RBAC, telemetría, turnos, QR
│   │   ├── views_fase3.py           # Flota, perfil, cierre de turno, admin
│   │   ├── urls.py                  # Rutas Fase 1 + 2 + 3
│   │   ├── permissions.py           # EsAdmin, EsConductor, EsCliente, ...
│   │   ├── security.py              # Argon2id, OTP, anti-spoofing, hash
│   │   ├── crypto.py                # Fernet para OTP
│   │   ├── mongo.py                 # Pool + índices + insert GeoJSON
│   │   ├── migrations/
│   │   └── management/commands/
│   │       ├── wait_for_db.py
│   │       ├── seed_conatacoch.py
│   │       ├── seed_carga.py        # Flota sintética para pruebas de carga
│   │       └── init_mongo_indexes.py
│   └── tests/                       # 64 pruebas (pytest)
│
├── web-admin/
│   ├── index.html                   # SPA mobile-first (login + 4 vistas)
│   ├── nginx.conf                   # Estáticos + proxy /api, /admin, /static
│   └── assets/
│       ├── styles.css               # Paleta estricta y layout de teléfono
│       ├── app.js                   # Cliente API, rol, mapa, QR, CRUD
│       ├── favicon.svg
│       └── recorridos_conatacoch.json  # Catálogo oficial (660 filas)
│
├── android-app/
│   ├── settings.gradle.kts / build.gradle.kts
│   ├── gradle.properties            # CONATACOCH_API_BASE_URL
│   ├── gradlew / gradlew.bat
│   └── app/src/main/
│       ├── AndroidManifest.xml
│       ├── java/cl/conatacoch/app/
│       │   ├── core/                # Red, sesión, GPS, QR, feedback
│       │   ├── domain/              # Modelos y contratos de repositorio
│       │   ├── data/                # DTOs, mappers, repositorios
│       │   └── ui/                  # Login, pasajero, conductor, admin
│       └── res/                     # Tema, strings, drawables, XML
│
└── docs/
    ├── arquitectura-4plus1.md
    ├── modelo-datos.md
    ├── despliegue.md
    └── GUIA_EVIDENCIAS_Y_GIT.md     # Capturas y comandos Git por rama
```

---

## 4. Inicio rápido

### 4.1 Prerrequisitos

- Docker Engine / Docker Desktop con **Compose v2** (`docker compose version`).
- 4 GB de RAM libres recomendados.
- Opcional: cuenta **MongoDB Atlas** para el camino de producción.
- Opcional: Python 3.12, Node 22 y Android Studio para desarrollo sin Docker.

### 4.2 Configuración

```bash
cp .env.example .env
```

En PowerShell:

```powershell
Copy-Item .env.example .env
```

Generar secretos reales:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"   # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"   # JWT_SECRET
```

Editar `.env` y definir al menos:

```dotenv
SECRET_KEY=<64+ caracteres aleatorios>
JWT_SECRET=<64+ caracteres aleatorios>
MYSQL_ROOT_PASSWORD=<password fuerte>
MYSQL_PASSWORD=<password fuerte>
```

### 4.3 Levantar el entorno

**Opción A — demo completa sin Atlas (Mongo local):**

```bash
docker compose --profile mongo-local up -d --build
```

**Opción B — MongoDB Atlas (recomendada para producción):**

```dotenv
MONGO_ATLAS_URI=mongodb+srv://usuario:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

```bash
docker compose up -d --build
```

Al iniciar, el backend ejecuta automáticamente:

```text
wait_for_db -> migrate -> seed_conatacoch -> init_mongo_indexes -> gunicorn
```

### 4.4 URLs

| Servicio | URL |
|---|---|
| Panel web (Nginx) | <http://localhost:8080> |
| Swagger UI | <http://localhost:8080/api/docs/> |
| ReDoc | <http://localhost:8080/api/redoc/> |
| Esquema OpenAPI | <http://localhost:8080/api/schema/> |
| Health / readiness | <http://localhost:8080/api/health/> |
| Liveness | <http://localhost:8080/api/health/live/> |
| Django Admin | <http://localhost:8080/admin/> |
| MySQL (solo local) | `localhost:3306` |
| MongoDB local (perfil) | `localhost:27017` |
| Backend directo (solo dev) | `http://localhost:8000` con `docker-compose.dev.yml` |

El backend **no publica puerto en producción**: todo entra por Nginx, lo que
permite escalar réplicas sin conflictos de puertos.

### 4.5 Modo desarrollo

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Expone `http://localhost:8000` y activa `DEBUG=True` sin montar código fuente.

---

## 5. Credenciales de prueba

Creadas por `seed_conatacoch` con hashing Argon2id/PBKDF2 de Django.

| Rol | RUT | Email | Password | Folio | Patente |
|---|---|---|---|---|---|
| **ADMIN** | `11.111.111-1` | `admin@conatacoch.cl` | `AdminConata2026!` | — | — |
| **CONDUCTOR** | `22.222.222-2` | `conductor1@conatacoch.cl` | `Conduc2026!` | `234001` | `ABCD-12` |
| **CONDUCTOR** | `33.333.333-3` | `conductor2@conatacoch.cl` | `Conduc2026!` | `236001` | `EFGH-34` |
| **CLIENTE** | `44.444.444-4` | `pasajero1@conatacoch.cl` | `Pasajero2026!` | — | — |
| **CLIENTE** | `55.555.555-5` | `pasajero2@conatacoch.cl` | `Pasajero2026!` | — | — |

> ⚠️ **Solo demo.** Cambiar obligatoriamente antes de producción.

---

## 6. Arquitectura — Modelo 4+1

El diseño sigue **Kruchten (1995)**: cuatro vistas de soporte (Lógica,
Procesos, Desarrollo, Física) y una vista de Escenarios que las valida.

### 6.1 Vista Lógica

Describe **qué** hace el sistema y cómo se descompone en capas y módulos.

```mermaid
flowchart LR
    subgraph Presentacion["Presentación"]
        WEB["web-admin<br/>HTML/CSS/JS mobile-first"]
        AND["android-app<br/>Kotlin + Compose"]
    end

    subgraph Aplicacion["Aplicación"]
        NGX["Nginx<br/>reverse proxy"]
        API["Django 5 + DRF"]
        JWT["SimpleJWT<br/>access / refresh"]
        OAS["drf-spectacular<br/>OpenAPI 3"]
        RBAC["Permisos RBAC<br/>EsAdmin / EsConductor / EsCliente"]
    end

    subgraph Dominio["Dominio CONATACOCH"]
        MOD["Modelos 3FN<br/>Usuario, Línea, Vehículo,<br/>Conductor, Paradero, Pago"]
        SEED["seed_conatacoch"]
        SEC["Argon2id, OTP Fernet,<br/>anti-spoofing, hash de token"]
    end

    subgraph Datos["Persistencia poliglota"]
        MYSQL[("MySQL 8<br/>conatacoch")]
        MONGO[("MongoDB Atlas<br/>telemetria_ubicacion")]
    end

    WEB --> NGX --> API
    AND --> NGX
    API --> JWT
    API --> OAS
    API --> RBAC
    API --> MOD
    MOD --> MYSQL
    SEED --> MYSQL
    API --> SEC
    API -->|"pool PyMongo"| MONGO
```

| Capa | Módulos | Responsabilidad |
|---|---|---|
| Presentación | `web-admin/`, `android-app/` | Panel mobile-first y app nativa |
| Borde | `web-admin/nginx.conf` | TLS termination (externo), estáticos, proxy |
| Aplicación | `core/views*.py`, `serializers*.py`, `urls.py` | Contratos REST, permisos, paginación |
| Seguridad | `settings.py`, `security.py`, `permissions.py`, `crypto.py` | JWT, Argon2id, OTP, RBAC, anti-spoofing |
| Dominio | `core/models.py` | Entidades, reglas, constraints, índices |
| Datos | MySQL + `mongo.py` | Transacciones 3FN y telemetría GeoJSON |
| Operación | `entrypoint.sh`, comandos | Migración, seed, índices, health |

**Decisiones clave**

- **Usuario único con discriminador `rol`** en lugar de tablas separadas por
  rol: evita duplicación de credenciales y mantiene una sola identidad.
- **`LineaColectiva`** modela el itinerario como entidad; la clave natural es
  `(folio, nombre_recorrido, tipo_trazado)` porque el dataset repite folios y
  pares folio/nombre.
- **`Conductor.folio_conatacoch`** es un dato operativo del turno (puede diferir
  del folio asignado al vehículo en relevos), por lo que no es redundante.
- **`TransaccionPago`** referencia líneas y conductor con `PROTECT` para
  preservar trazabilidad financiera.
- **MongoDB** no reemplaza a MySQL: se usa solo para telemetría de alta
  escritura con patrón *write-heavy, read-latest*, TTL y consultas geoespaciales.
- **Fase 3 es aditiva**: `views_fase3.py` y `serializers_fase3.py` no modifican
  la lógica validada de Fase 2; solo agregan endpoints de apoyo para mapas,
  perfil y CRUD administrativo.

### 6.2 Vista de Procesos

Describe **cómo** fluyen los procesos concurrentes y de arranque.

**Arranque del contenedor (idempotente):**

```mermaid
sequenceDiagram
    autonumber
    participant C as Compose
    participant B as Backend entrypoint
    participant M as MySQL
    participant A as MongoDB
    participant G as Gunicorn

    C->>M: inicia db_mysql + healthcheck
    M-->>C: healthy
    C->>B: inicia backend (depends_on healthy)
    B->>M: wait_for_db (SELECT 1)
    B->>M: migrate --noinput
    B->>M: seed_conatacoch (update_or_create)
    B->>A: init_mongo_indexes (2dsphere + TTL)
    Note over B,A: Si Mongo falla, se registra advertencia<br/>y el API arranca igual (degraded)
    B->>G: exec gunicorn (workers x threads)
```

**Solicitud HTTP típica:**

```mermaid
sequenceDiagram
    autonumber
    participant U as Navegador / App
    participant N as Nginx
    participant G as Gunicorn
    participant D as Django/DRF
    participant Q as MySQL

    U->>N: GET /api/lineas/?comuna=Melipilla
    N->>G: proxy_pass (resolver Docker)
    G->>D: WSGI (worker gthread)
    D->>D: throttling + permisos
    D->>Q: SELECT ... WHERE comuna ... LIMIT 25
    Q-->>D: filas
    D-->>N: JSON paginado
    N-->>U: 200 OK
```

**Pago QR de punta a punta:**

```mermaid
sequenceDiagram
    autonumber
    participant P as Pasajero
    participant API as API Django
    participant M as MySQL
    participant C as Conductor

    P->>API: POST /api/pagos/qr/ {conductor_id, linea_id, monto}
    API->>M: INSERT transaccion (PENDIENTE, UUID)
    API-->>P: {codigo_qr_uuid, estado, monto}
    P->>P: Render QR local (ZXing / qrcode-generator)
    C->>API: GET /api/transacciones/?estado=PENDIENTE
    API-->>C: pago pendiente
    C->>C: Alerta visual + sonora
    C->>API: POST /api/pagos/confirmar/ {codigo_qr_uuid}
    API->>M: UPDATE estado=PAGADO
    P->>API: GET /api/transacciones/?search=uuid
    API-->>P: estado PAGADO
```

**Procesos concurrentes y garantías**

| Proceso | Concurrencia | Garantía |
|---|---|---|
| API de lectura | Workers/threads Gunicorn | Sin estado compartido; cualquier réplica responde |
| Seed | `transaction.atomic()` al arrancar | Todo o nada; `update_or_create` evita duplicados |
| Migraciones | Un solo contenedor al inicio | Idempotentes; en multi-réplica usar job aparte |
| Índices Mongo | Idempotentes (`create_index`) | Seguro reejecutar; TTL 14400 s |
| Pago | Transacción + RESTRICT | No se borran referencias financieras |
| Telemetría | Inserción append-only | TTL elimina documentos > 4 h |
| GPS conductor | Corrutina cada 5 s | Una sola sesión activa; anti-spoofing en servidor |
| Polling de pagos | Cada 5 s en conductor | Detección de pagos nuevos y alerta sonora |

**Estado y sesiones:** las sesiones viven en MySQL
(`django.contrib.sessions.backends.db`), la autenticación API es JWT y no hay
archivos locales. Esto habilita escalado horizontal sin *sticky sessions*.

### 6.3 Vista de Desarrollo

Describe la organización del equipo, el monorepo y el flujo de trabajo.

| Área | Responsable | Artefactos |
|---|---|---|
| Infraestructura | DevOps / Cloud | Compose, Dockerfile, `.env`, redes, volúmenes |
| Backend / datos | Full-stack / Data | `core/`, migraciones, seed, índices Mongo |
| Frontend admin | Frontend | `web-admin/` |
| Mobile | Android | `android-app/` |
| Calidad | QA | `backend/tests/`, `bench_baseline.py`, OpenAPI |

**Convenciones**

- Dominio en español (`LineaColectiva`, `Paradero`); framework en inglés.
- Configuración **solo** por variables de entorno (12-factor).
- Cambios de esquema siempre vía migraciones versionadas.
- Fase 3 no toca archivos validados de Fase 1/2: agrega módulos nuevos.
- Secretos nunca en Git (`.env` ignorado; `.env.example` documenta el contrato).
- Imagen inmutable: sin bind mounts de código en producción.
- App Android sin `google-services.json`: mapas con OSMDroid y QR con ZXing.

**Flujo para agregar una entidad**

```bash
# 1. Editar backend/core/models.py
# 2. Migración
docker compose exec backend python manage.py makemigrations core
docker compose exec backend python manage.py migrate
# 3. Serializer + ViewSet + router
# 4. Pruebas
docker compose exec backend python -m pytest tests/ -q
# 5. Documentación automática en /api/docs/
```

**Ejecución local sin Docker (útil para pruebas)**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:DB_ENGINE="django.db.backends.sqlite3"
$env:SQLITE_PATH="$env:TEMP\conatacoch.sqlite3"
$env:SECRET_KEY="dev-only"
cd backend
python manage.py migrate
python manage.py seed_conatacoch
python -m pytest tests/ -q
```

### 6.4 Vista Física

Describe el despliegue, nodos, contenedores, redes y volúmenes.

```mermaid
flowchart TB
    subgraph Host["Host Docker / VM / Cloud"]
        subgraph Net["conatacoch_net (bridge interno)"]
            NGX["web_admin<br/>nginx:1.27-alpine<br/>:80 publicado"]
            BE1["backend #1<br/>python:3.12-slim<br/>Gunicorn :8000"]
            BE2["backend #2..N<br/>(scale)"]
            DB["db_mysql<br/>mysql:8.0<br/>:3306"]
            ML["mongo_local<br/>mongo:8.0<br/>(perfil opcional)"]
        end
        V1[("conatacoch_mysql_data")]
        V2[("conatacoch_mongo_data")]
    end

    INTERNET["Internet / LAN"] -->|":8080"| NGX
    MOBILE["App Android"] -->|"HTTPS / LAN"| NGX
    NGX -->|"proxy /api /admin /static"| BE1
    NGX --> BE2
    BE1 --> DB
    BE2 --> DB
    BE1 -.->|"solo si MONGO_ATLAS_URI vacío"| ML
    BE1 -->|"TLS 27017"| ATLAS[("MongoDB Atlas<br/>telemetria_ubicacion")]
    DB --- V1
    ML --- V2
```

| Servicio | Imagen | Puertos | Volumen | Healthcheck |
|---|---|---|---|---|
| `db_mysql` | `mysql:8.0` | `3306:3306` (solo local) | `conatacoch_mysql_data` | `mysqladmin ping` |
| `backend` | build `backend/Dockerfile` | interno `8000` | ninguno (read-only) | `GET /api/health/live/` |
| `web_admin` | `nginx:1.27-alpine` | `${WEB_ADMIN_PORT:-8080}:80` | montajes `:ro` | `GET /healthz` |
| `mongo_local` | `mongo:8.0` | `27017:27017` | `conatacoch_mongo_data` | `mongosh ping` |

**Topología de producción recomendada**

```text
Internet
   │ HTTPS 443
   ▼
Load Balancer / WAF / CDN (TLS, rate limit, gzip)
   │ HTTP 80 (red privada)
   ▼
web_admin (Nginx)  ──►  backend x N (Gunicorn)
                              │
                ┌─────────────┴──────────────┐
                ▼                            ▼
        MySQL 8 (primary)            MongoDB Atlas
        + read replica (futuro)      replica set gestionado
```

- MySQL **no** se publica a Internet; solo `conatacoch_net`.
- Atlas se consume por TLS (`mongodb+srv`).
- El backend puede correr en varias réplicas porque no escribe estado local.
- Los volúmenes solo almacenan MySQL/Mongo local; el backend no persiste nada.

### 6.5 Vista de Escenarios

Valida que las otras cuatro vistas cubren los casos de uso reales.

| # | Escenario | Actores | Flujo resumido | Componentes |
|---|---|---|---|---|
| E1 | Administrador consulta recorridos | Admin | Login JWT → panel → filtro comuna | Nginx, DRF, MySQL |
| E2 | Pasajero busca un colectivo | Pasajero | Abre panel/app → filtra origen/destino | Nginx, DRF, MySQL |
| E3 | Conductor inicia turno | Conductor | Login → OTP → `en_turno` → telemetría | DRF, MySQL, Atlas |
| E4 | Pago con QR | Pasajero + conductor | Genera UUID → alerta → confirma → estado | DRF, MySQL, JWT |
| E5 | Operador revisa salud | DevOps | `/api/health/` → MySQL + Mongo | Nginx, DRF, Atlas |
| E6 | Arranque/recuperación | DevOps | Compose levanta → migrate + seed | Docker, MySQL |
| E7 | Admin gestiona flota | Admin | CRUD conductor/línea/tarifa | Nginx, DRF, MySQL |
| E8 | Pasajero ve flota en vivo | Pasajero | Mapa + ETA + cupos | Leaflet/OSMDroid, Atlas |

**Escenario E2 — búsqueda pública:**

```mermaid
sequenceDiagram
    autonumber
    participant P as Pasajero
    participant W as Panel web / App
    participant A as API /api/lineas
    participant D as MySQL

    P->>W: escribe "Melipilla"
    W->>A: GET /api/lineas/?search=Melipilla&page_size=25
    A->>D: full-text LIKE + índices de comuna
    D-->>A: resultados paginados
    A-->>W: JSON
    W-->>P: tabla de recorridos y tarifas
```

**Escenario E4 — pago QR:** ver diagrama de la Vista de Procesos.

---

## 7. Bases de datos

### 7.1 MySQL 8.0 — modelo relacional en 3FN

Base: `conatacoch`, charset `utf8mb4`, collation `utf8mb4_0900_ai_ci`.

| Entidad | PK | Atributos principales | Claves / índices |
|---|---|---|---|
| `usuario` | `id` | rut, nombre, email, password_hash, rol, activo, intentos_fallidos, bloqueado_hasta | `rut` UNIQUE, `email` UNIQUE, `rol+activo`, `bloqueado_hasta` |
| `linea_colectiva` | `id` | region, folio, tipo_servicio, nombre_recorrido, tipo_trazado, origen/destino, tarifa_actual | `folio` INDEX, `(folio,nombre_recorrido,tipo_trazado)` UNIQUE, `(region,folio)`, comunas |
| `vehiculo` | `id` | patente, marca_modelo, capacidad_pasajeros, linea_id | `patente` UNIQUE, `linea` INDEX |
| `conductor` | `id` | usuario_id, folio_conatacoch, vehiculo_id, en_turno, cupos_disponibles, otp_secreto, token_sesion_activa | `folio_conatacoch`, `(en_turno,folio)`, `(vehiculo,en_turno)` |
| `paradero` | `id` | nombre, comuna, latitud, longitud, linea_id | `(linea,nombre)` UNIQUE, `(comuna,linea)`, `(latitud,longitud)` |
| `transaccion_pago` | `id` | codigo_qr_uuid, pasajero_id, conductor_id, linea_id, monto, fecha_hora, estado | `codigo_qr_uuid` UNIQUE, `(conductor,fecha)`, `(linea,fecha)`, `(pasajero,fecha)`, `(estado,fecha)` |

**Justificación 3FN**

1. **1FN:** todos los atributos son atómicos. No hay listas de paraderos ni
   arreglos embebidos; los paraderos son filas propias con FK.
2. **2FN:** la PK surrogate `id` no genera dependencias parciales; la clave
   natural compuesta se declara como restricción única y todos los atributos
   dependen del itinerario completo.
3. **3FN:** no hay dependencias transitivas entre atributos no clave. Comunas,
   orígenes y destinos son atributos del recorrido; no se almacena una tabla de
   comunas duplicada ni el nombre de la línea dentro del vehículo, conductor o
   pago (solo la FK).
4. **Sin redundancia controlada:** `tarifa_actual` es el valor vigente de la
   línea; un historial de tarifas sería una tabla adicional futura.
5. **Clave natural del dataset:** 660 filas producen 617 pares
   `(folio, nombre_recorrido)`; al agregar `tipo_trazado` se obtienen 660
   combinaciones únicas. Por eso la restricción es triple y no `folio` solo.

**Integridad referencial**

- Todas las FK usan `on_delete=PROTECT` en Django, equivalente ORM a
  `ON DELETE RESTRICT`.
- MySQL/InnoDB aplica **RESTRICT por defecto** a las FK.
- Restricciones `CHECK`: montos y tarifas ≥ 0, capacidades 1–30, coordenadas en
  rango, cupos 0–30, region/folio > 0.

**Índices B-Tree** (nombres reales de la migración)

```text
usuario:            idx_usuario_rol_activo, idx_usuario_bloqueado
                    + UNIQUE(rut), UNIQUE(email)
linea_colectiva:    idx_linea_region_folio, idx_linea_comuna_origen,
                    idx_linea_comuna_destino
                    + UNIQUE(folio, nombre_recorrido, tipo_trazado)
vehiculo:           idx_vehiculo_linea + UNIQUE(patente)
conductor:          idx_conductor_folio, idx_conductor_turno,
                    idx_conductor_vehiculo
paradero:           idx_paradero_comuna_linea, idx_paradero_geo
                    + UNIQUE(linea, nombre)
transaccion_pago:   idx_pago_conductor_fecha, idx_pago_linea_fecha,
                    idx_pago_pasajero_fecha, idx_pago_estado_fecha
                    + UNIQUE(codigo_qr_uuid)
```

### 7.2 Pool de conexiones MySQL

```python
"CONN_MAX_AGE": 600,          # reutiliza conexiones 10 minutos
"CONN_HEALTH_CHECKS": True,   # valida antes de reutilizar
"OPTIONS": {
    "charset": "utf8mb4",
    "init_command": "SET sql_mode='STRICT_TRANS_TABLES,...'",
    "connect_timeout": 10,
}
```

Gunicorn usa `gthread` con `GUNICORN_WORKERS=3` y `GUNICORN_THREADS=4`.

### 7.3 MongoDB Atlas — `telemetria_ubicacion`

**Documento GeoJSON** (colección `ubicaciones`):

```json
{
  "_id": { "$oid": "675f..." },
  "id_vehiculo": 12,
  "id_conductor": 4,
  "folio_linea": "234001",
  "cupos_disponibles": 3,
  "ubicacion": { "type": "Point", "coordinates": [-70.6693, -33.4489] },
  "velocidad_kmh": 38.5,
  "rumbo": 270,
  "timestamp": { "$date": "2026-11-22T14:30:00Z" }
}
```

> GeoJSON usa orden **`[longitud, latitud]`**. El timestamp se guarda en UTC.

**Índices creados automáticamente** (`init_mongo_indexes`, idempotente):

| Nombre | Claves | Opción | Propósito |
|---|---|---|---|
| `idx_ubicacion_2dsphere` | `ubicacion` | `2dsphere` | `$near`, `$geoWithin`, distancia |
| `idx_folio_timestamp` | `folio_linea: 1, timestamp: -1` | — | Última posición por recorrido |
| `idx_timestamp_ttl` | `timestamp: 1` | `expireAfterSeconds: 14400` | Retención 4 horas |
| `idx_vehiculo_timestamp` | `id_vehiculo: 1, timestamp: -1` | — | Última posición por vehículo |

**Selección del backend:** si `MONGO_ATLAS_URI` tiene valor se usa Atlas con
`tls=True`; si está vacío se usa `MONGO_LOCAL_URI`
(`mongodb://mongo_local:27017`). El cliente se crea una vez por proceso con
`maxPoolSize=50`, `minPoolSize=5` y `serverSelectionTimeoutMS=5000`.

---

## 8. Carga inicial idempotente

**Comando:** `python manage.py seed_conatacoch`

Se ejecuta automáticamente si `SEED_ON_START=true` (default). Es seguro
reejecutarlo: usa `update_or_create` con las claves naturales.

| Paso | Resultado |
|---|---|
| Lee `recorridos_conatacoch_taxi_colectivo_2.json` | 660 itinerarios |
| `update_or_create` por `(folio, nombre_recorrido, tipo_trazado)` | 660 líneas |
| Crea paraderos de origen/destino por línea | 1.320 paraderos |
| Crea usuarios, vehículos y conductores demo | 5 usuarios, 2 vehículos, 2 conductores |
| Asigna tarifa demo | urbana 1.000 CLP / rural 1.500 CLP |
| Cifra OTP de conductores y deja token vacío | Secretos protegidos |

**Paraderos:** se usa el centroide aproximado de cada comuna de la Región
Metropolitana (mapa de 48 comunas) más un *jitter* determinístico de ~1 km
derivado de SHA-256. Es data base para desarrollo; en producción se reemplaza
por geocodificación real.

**Opciones útiles**

```bash
python manage.py seed_conatacoch --skip-paraderos
python manage.py seed_conatacoch --skip-usuarios
python manage.py seed_conatacoch --data-file /ruta/otro.json
python manage.py seed_conatacoch --tarifa-urbana 1200 --tarifa-rural 1800
python manage.py seed_carga --conductores 50    # flota sintética para carga
```

---

## 9. Escalabilidad horizontal

### 9.1 Backend sin estado

| Requisito stateless | Implementación |
|---|---|
| Sesiones no locales | `SESSION_ENGINE` en MySQL |
| Auth API | JWT firmado; no hay sesión de servidor |
| Archivos subidos | No existen; media iría a S3/Blob |
| Logs | `stdout` (Docker logging driver) |
| Configuración | Variables de entorno |
| Filesystem | Contenedor `read_only: true` + `tmpfs /tmp` |
| Seed/migraciones | Al arranque, idempotentes |
| Balanceo | Nginx con `resolver 127.0.0.11` re-resuelve `backend` |

**Escalar:**

```bash
docker compose up -d --scale backend=3
```

Nginx descubre las IPs nuevas vía DNS de Docker:

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
set $backend_upstream http://backend:8000;
proxy_pass $backend_upstream;
```

No se requiere *sticky session* ni afinidad de sesión.

### 9.2 Capacidad de conexiones

```text
conexiones ≈ replicas_backend × GUNICORN_WORKERS × GUNICORN_THREADS
```

| Réplicas | Workers | Threads | Conexiones aprox. | MySQL `max_connections=300` |
|---|---|---|---|---|
| 1 | 3 | 4 | 12 | 4 % |
| 3 | 3 | 4 | 36 | 12 % |
| 8 | 3 | 4 | 96 | 32 % |

### 9.3 Estrategia por capa

| Capa | Ahora | Siguiente |
|---|---|---|
| Web/API | Nginx + N réplicas Gunicorn | HPA/autoescalado, CDN, WAF |
| MySQL | Un primary con índices | Read replicas, partición de `transaccion_pago` |
| Mongo | Atlas replica set + TTL | Sharding por `folio_linea`, time series |
| Cache | Sin cache | Redis para tarifas/recorridos y rate limit |
| Asincronía | Sin colas | Celery/SQS para pagos y notificaciones |
| Mobile | Polling cada 5–12 s | Push notifications / WebSocket |

---

## 10. Seguridad

| Control | Implementación |
|---|---|
| Password hashing | **Argon2id** (`hash_password_argon2id`) con rehash transparente; PBKDF2 legacy soportado |
| JWT | `HS256` con `JWT_SECRET`; **access 15 min**, refresh 7 días, rotación |
| Autorización | RBAC: `EsAdmin`, `EsConductor`, `EsCliente`, `PuedeIniciarTurno`, `EsAdminOPropietarioRecurso` |
| Fuerza bruta | 5 intentos fallidos → bloqueo 15 min (`intentos_fallidos`, `bloqueado_hasta`) |
| OTP | 6 dígitos, cifrado Fernet (AES + HMAC), expiración configurable, un solo uso |
| Token de sesión | Solo hash SHA-256 en `token_sesion_activa` |
| Anti-spoofing GPS | Haversine + `calcular_velocidad_kmh`; rechaza > 130 km/h con HTTP 422 |
| Validación de entrada | Serializers DRF; RUT/patente con dígito verificador |
| Auto-registro seguro | `/api/auth/registro/` fuerza rol `CLIENTE`, email único, RUT módulo 11 y política de contraseñas; no permite crear ADMIN/CONDUCTOR |
| Pagos | UUID único, monto > 0, estado controlado, `PROTECT` en FKs |
| Throttling | `AnonRateThrottle 60/min`, `UserRateThrottle 600/min` |
| Secretos | `.env` fuera de Git; `.env.example` como contrato |
| Contenedor | Usuario `appuser` UID 10001, `read_only`, `tmpfs`, sin privilegios |
| Cabeceras | `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` |
| ORM | Consultas parametrizadas; sin SQL concatenado |
| Mobile | `EncryptedSharedPreferences`; logs sin tokens; tráfico claro solo en dev |

**Tabla de endpoints y permisos (Fase 2 + Fase 3)**

| Método | Endpoint | Permiso | Descripción |
|---|---|---|---|
| POST | `/api/auth/login/` | Público | Login Argon2id + anti-fuerza bruta |
| POST | `/api/auth/refresh/` | Público | Renovar access token |
| POST | `/api/auth/registro/` | Público | Auto-registro de pasajeros (siempre rol `CLIENTE`) |
| GET | `/api/lineas/` | Público | Catálogo de recorridos |
| GET | `/api/paraderos/` | Público | Paraderos por línea/comuna |
| GET | `/api/vehiculos/` | JWT | Flota |
| GET | `/api/conductores/` | JWT | Conductores |
| GET | `/api/transacciones/` | JWT | Pagos y estados |
| GET | `/api/telemetria/flota/` | JWT | Última posición de la flota en turno |
| POST | `/api/eta/calcular/` | Cliente | ETA y opciones cercanas |
| POST | `/api/telemetria/enviar/` | Conductor | Ingesta GPS anti-spoofing |
| POST | `/api/conductor/iniciar-turno/` | Conductor | OTP de inicio de turno |
| POST | `/api/conductor/finalizar-turno/` | Conductor | OTP de cierre de turno |
| GET | `/api/conductor/perfil/` | Conductor | Perfil, vehículo y línea |
| POST | `/api/conductor/cupos/` | Conductor | Actualizar cupos disponibles |
| POST | `/api/pagos/qr/` | Cliente | Crear pago QR |
| POST | `/api/pagos/confirmar/` | Conductor | Confirmar pago QR |
| GET | `/api/admin-api/conductores/` | Admin | Listado de conductores |
| POST | `/api/admin-api/conductores/registro/` | Admin | Alta de conductor |
| POST | `/api/admin-api/conductores/completo/` | Admin | Alta usuario + vehículo + conductor |
| GET/PATCH/DELETE | `/api/admin-api/conductores/<id>/` | Admin | Detalle, edición y baja |
| POST | `/api/admin-api/lineas/` | Admin | Crear/actualizar línea |
| POST | `/api/admin-api/lineas/upsert/` | Admin | Upsert idempotente de línea |
| POST | `/api/admin-api/tarifas/` | Admin | Actualizar tarifa |
| GET | `/api/health/`, `/api/health/live/` | Público | Readiness / liveness |
| GET | `/api/stats/` | Público | Agregados del panel |

**Checklist antes de producción**

- [ ] Rotar las 5 passwords demo y eliminar usuarios de prueba.
- [ ] Generar `SECRET_KEY` y `JWT_SECRET` de 64+ caracteres.
- [ ] `DEBUG=False`, `SECURE_SSL_REDIRECT=True`, cookies `Secure`.
- [ ] TLS en el load balancer y `CSRF_TRUSTED_ORIGINS` con el dominio real.
- [ ] Eliminar la publicación del puerto 3306 de `db_mysql`.
- [ ] Restringir Atlas por IP/VPC y usar usuario con privilegios mínimos.
- [ ] Configurar backups de MySQL y snapshots de Atlas.
- [ ] Centralizar logs y alertas de `/api/health/`.

---

## 11. API REST

Documentación interactiva: **`/api/docs/`** (Swagger) y **`/api/redoc/`**.
Esquema: **`/api/schema/`** (OpenAPI 3).

### 11.1 Fase 1 — lectura y salud

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| GET | `/api/health/live/` | Público | Liveness |
| GET | `/api/health/` | Público | Readiness MySQL + Mongo |
| GET | `/api/stats/` | Público | Agregados para el panel |
| GET | `/api/lineas/` | Público | Filtros `comuna`, `folio`, `region`, `tipo_servicio`, `search` |
| GET | `/api/lineas/{id}/` | Público | Detalle de recorrido |
| GET | `/api/paraderos/` | Público | Filtros `comuna`, `linea` |
| GET | `/api/vehiculos/` | JWT | Flota; filtro `linea` |
| GET | `/api/conductores/` | JWT | Conductores; filtros `en_turno`, `folio` |
| GET | `/api/transacciones/` | JWT | Pagos; filtros `estado`, `conductor`, `linea`, `pasajero`, `desde`, `hasta`, `search` |
| POST | `/api/token/` | Público | Access + refresh (compatibilidad) |
| POST | `/api/token/refresh/` | Público | Renovar access |
| POST | `/api/token/verify/` | Público | Verificar token |

### 11.2 Fase 2 — operación segura

| Método | Endpoint | Auth | Request / Response |
|---|---|---|---|
| POST | `/api/auth/login/` | Público | `{email, password}` → `{access, refresh, usuario, access_expires_in}` |
| POST | `/api/auth/refresh/` | Público | `{refresh}` → `{access}` |
| POST | `/api/auth/registro/` | Público | `{rut, nombre, email, password, password_confirm}` → `{access, refresh, usuario.rol=CLIENTE}` |
| POST | `/api/admin-api/conductores/registro/` | Admin | Alta de conductor con usuario y vehículo |
| GET | `/api/admin-api/conductores/` | Admin | Listado paginado con búsqueda |
| POST | `/api/admin-api/lineas/` | Admin | Crear/actualizar línea |
| POST | `/api/admin-api/tarifas/` | Admin | `{linea_id, tarifa}` |
| POST | `/api/eta/calcular/` | Cliente | `{linea_id, latitud_pasajero, longitud_pasajero}` → opciones con ETA |
| POST | `/api/telemetria/enviar/` | Conductor | `{latitud, longitud, velocidad_kmh, rumbo, cupos_disponibles, timestamp}` |
| POST | `/api/conductor/iniciar-turno/` | Conductor | `{solicitar_codigo:true}` → `{estado, codigo_otp, expires_in_minutes}`; luego `{codigo_otp}` |
| POST | `/api/conductor/cupos/` | Conductor | `{cupos_disponibles}` |
| POST | `/api/pagos/qr/` | Cliente | `{conductor_id, linea_id, monto}` → `{codigo_qr_uuid, estado, monto, ...}` |
| POST | `/api/pagos/confirmar/` | Conductor | `{codigo_qr_uuid}` → pago `PAGADO` |

### 11.3 Fase 3 — soporte de interfaces

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| GET | `/api/telemetria/flota/` | JWT | Última posición de cada conductor en turno; filtro `linea_id` |
| GET | `/api/conductor/perfil/` | Conductor | Perfil, vehículo, línea y cupos |
| POST | `/api/conductor/finalizar-turno/` | Conductor | OTP de cierre y limpieza de sesión de turno |
| POST | `/api/admin-api/conductores/completo/` | Admin | Alta transaccional usuario + vehículo + conductor |
| GET | `/api/admin-api/conductores/<id>/` | Admin | Detalle administrativo |
| PATCH | `/api/admin-api/conductores/<id>/` | Admin | Edición parcial |
| DELETE | `/api/admin-api/conductores/<id>/` | Admin | Baja con protección de referencias |
| POST | `/api/admin-api/lineas/upsert/` | Admin | Alta/actualización idempotente por clave natural |

### Ejemplo de autenticación

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@conatacoch.cl","password":"AdminConata2026!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s http://localhost:8080/api/conductores/ \
  -H "Authorization: Bearer $TOKEN"
```

PowerShell:

```powershell
$body = @{ email="admin@conatacoch.cl"; password="AdminConata2026!" } | ConvertTo-Json
$token = (Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/auth/login/" `
  -ContentType "application/json" -Body $body).access
Invoke-RestMethod -Uri "http://localhost:8080/api/conductores/" `
  -Headers @{ Authorization = "Bearer $token" }
```

### Paginación

`?page=2&page_size=50` (máximo 100). Respuesta estándar DRF:
`count`, `next`, `previous`, `results`.

---

## 12. Panel web mobile-first

`web-admin/` es una SPA sin build step servida por Nginx. Se ve como una app de
teléfono centrada en escritorio y a pantalla completa en móvil.

**Paleta estricta**

```css
--cona-black:  #0B0B0B;
--cona-white:  #FFFFFF;
--cona-yellow: #FFD100;
```

No se usan otros colores: los grises son transparencias del blanco.

**Vistas**

| Vista | Funcionalidad |
|---|---|
| Login | Email + password, detección automática de rol, verificación de API |
| Pasajero | Búsqueda de recorridos, mapa Leaflet, ETA, cupos, pago QR en 2 toques |
| Conductor | Modo oscuro, inicio/cierre de turno con OTP, cupos, GPS periódico, alerta de pago QR |
| Administrador | CRUD de conductores, líneas, tarifas, flota en vivo y auditoría de pagos QR |
| Cuenta | Identidad, rol y cierre de sesión |

**Catálogo oficial:** `web-admin/assets/recorridos_conatacoch.json` contiene las
660 filas del dataset. El panel resuelve el `linea_id` de la base vía
`/api/lineas/?folio=...`, de modo que el catálogo y la API siempre coinciden.

**Ejecución local del panel**

```bash
# Servir estáticos y proxear /api al backend
docker compose up -d web_admin
# o sin Docker, con cualquier servidor estático + proxy
```

---

## 13. App Android

`android-app/` es una app nativa **Kotlin + Jetpack Compose + Material 3**
organizada con **MVVM + Clean Architecture**.

| Capa | Contenido |
|---|---|
| `ui` | `LoginScreen`, `PassengerScreen`, `DriverScreen`, `AdminScreen`, tema y componentes |
| `domain` | Modelos (`User`, `Linea`, `EtaResult`, `QrPayment`, ...) y contratos de repositorio |
| `data` | `ApiService` Retrofit, DTOs, mappers y repositorios |
| `core` | Sesión cifrada, JWT, red, GPS, QR, feedback sonoro/vibración |

**Pantallas obligatorias cubiertas**

- Login unificado con detección de rol, campo OTP y enlace de **auto-registro**
  para pasajeros nuevos.
- Pasajero: mapa OSMDroid con teselas Esri Dark (sin API key), ETA, cupos y
  pago QR en dos toques.
- Conductor: pantalla oscura de alto contraste, botones grandes, OTP de turno,
  cambio de asiento, GPS periódico y alerta visual/sonora de pago QR
  (`ToneGenerator`).
- Administrador: identidad y accesos al panel web.

**Configuración de API**

```properties
# android-app/gradle.properties
CONATACOCH_API_BASE_URL=http://10.0.2.2:8000/api/
```

| Entorno | URL |
|---|---|
| Emulador + backend local | `http://10.0.2.2:8000/api/` |
| Dispositivo en LAN | `http://<IP-del-PC>:8000/api/` |
| Producción | `https://<dominio>/api/` |

**Compilar**

```powershell
cd android-app
.\gradlew.bat :app:assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

Instrucciones completas en [`android-app/README.md`](android-app/README.md).

---

## 14. Pruebas, métricas y validación

### 14.1 Suite automatizada

```bash
cd backend
python -m pytest tests/ -q --tb=short
```

Resultado de la última ejecución:

```text
64 passed
```

Cobertura funcional:

- Seed completo e **idempotente** (660 líneas, 0 duplicados).
- 5 usuarios, 2 vehículos, 2 conductores; passwords verificados.
- Login Argon2id, bloqueo tras intentos fallidos, refresh JWT.
- RBAC: 401/403 por rol en endpoints protegidos.
- OTP de turno: solicitud, validación, expiración y cierre.
- Telemetría GPS: inserción GeoJSON, rechazo anti-spoofing, cupos.
- ETA: cálculo Haversine y ordenamiento por cercanía.
- Pago QR: creación, confirmación, estados y auditoría.
- CRUD admin de conductores y líneas.
- `PROTECT` impide borrar una línea referenciada.
- Health público y `degraded` cuando Mongo no responde.
- OpenAPI y Swagger responden 200.

### 14.2 Pruebas de carga (Fase 2)

Entorno: SQLite + `MONGO_MOCK=1`, servidor de desarrollo Django, cliente HTTP
concurrente. Las latencias incluyen el cliente y el GIL de Python, por lo que
son una **cota conservadora**.

| Escenario | Concurrencia | Éxitos | Promedio | p95 | p99 | Throughput |
|---|---|---|---|---|---|---|
| Telemetría GPS | 50 | 50/50 | **400.62 ms** | 1053.99 ms | 1058.00 ms | **44.70 req/s** |
| ETA pasajeros | 100 | 100/100 | **936.55 ms** | 1605.93 ms | 1662.52 ms | **55.86 req/s** |
| Login (150 usuarios) | 150 | 150/150 | — | — | — | 14.243 s total |

**Validaciones adicionales de la carga**

- 50 vehículos distintos detectados en 50 envíos GPS (`validacion_vehiculos_unicos: true`).
- 100 respuestas ETA con opciones (mínimo y máximo 50 opciones por respuesta).
- 0 errores HTTP en ambos escenarios.

Métricas crudas: `carga_metrics.json` (generado por `backend/tests/bench_baseline.py`).

### 14.3 Validación de build Android

```text
.\gradlew.bat :app:assembleDebug --no-daemon --console=plain
BUILD SUCCESSFUL in 4m 18s
37 actionable tasks: 37 executed
APK: app/build/outputs/apk/debug/app-debug.apk (11.5 MB)
```

### 14.4 Otras validaciones

```text
manage.py check                              -> 0 issues
manage.py makemigrations --check             -> sin cambios pendientes
manage.py spectacular --validate             -> schema válido
node --check web-admin/assets/app.js         -> OK
Parser XML de recursos Android               -> OK
```

---

## 15. Operación y troubleshooting

### Comandos útiles

```bash
docker compose ps
docker compose logs -f backend
docker compose exec backend python manage.py seed_conatacoch
docker compose exec backend python manage.py init_mongo_indexes
docker compose exec backend python -m pytest tests/ -q
docker compose exec db_mysql mysql -uconatacoch -p conatacoch -e "SHOW TABLES;"
docker compose --profile mongo-local exec mongo_local mongosh
```

### Reinicio limpio (destructivo)

```bash
docker compose down -v
docker compose --profile mongo-local up -d --build
```

`-v` elimina los volúmenes `conatacoch_mysql_data` y
`conatacoch_mongo_data`. No usar en producción.

### Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| Panel muestra MongoDB `degraded` | Atlas vacío y perfil local no iniciado | Configurar `MONGO_ATLAS_URI` o usar `--profile mongo-local` |
| `502 Bad Gateway` en panel | Backend aún arrancando/migrando | `docker compose logs -f backend`, esperar healthcheck |
| `port is already allocated` | Puerto 8080/3306 ocupado | Cambiar `WEB_ADMIN_PORT`/`MYSQL_EXPOSED_PORT` en `.env` |
| Backend reinicia en loop | Credenciales MySQL incorrectas o DB no lista | Revisar `.env`, `docker compose logs db_mysql` |
| `/api/docs/` sin estilos | Falta `collectstatic` en imagen | Reconstruir (`--build`) |
| App Android no conecta | URL de API incorrecta | Ajustar `CONATACOCH_API_BASE_URL` (`10.0.2.2` en emulador) |
| Mapa Android muestra «API KEY REQUIRED» | Versión antigua usaba CARTO | Actualizar la app: usa Esri Dark Gray sin API key |
| Mapa Android vacío | Sin red o tiles bloqueados | Verificar conexión; OSMDroid usa Esri Dark Gray |
| App Android no conecta en emulador | Backend en `127.0.0.1` o `DEBUG=False` | `runserver 0.0.0.0:8000`, `DEBUG=True` y `10.0.2.2:8000/api/` |
| QR no se dibuja | ZXing no pudo codificar | Revisar UUID y tamaño; regenerar pago |
| TTL no borra documentos | Monitor TTL corre cada ~60 s o índice ausente | Ejecutar `init_mongo_indexes`; esperar |
| Seed lento en MySQL | 660 líneas + 1.320 paraderos | Normal en primer arranque; usar `--skip-paraderos` en pruebas |

### Backups

```bash
# MySQL
docker compose exec db_mysql mysqldump -uconatacoch -p conatacoch > backup.sql

# Atlas: snapshots continuos del cluster gestionado
```

---

## 16. Trazabilidad con la rúbrica

| Criterio | Evidencia |
|---|---|
| **Estructura adecuada de la BD** | 6 entidades normalizadas, FK, `CHECK`, migración versionada |
| **Optimización y normalización (3FN)** | Justificación 3FN, índices B-Tree compuestos, clave natural validada |
| **Bases de datos en la nube** | MongoDB Atlas con TLS, pool PyMongo, `2dsphere`, TTL 4 h |
| **Patrones de seguridad** | Argon2id, JWT, RBAC, OTP Fernet, anti-spoofing, throttling, contenedor non-root |
| **Entorno Docker** | Compose con 4 servicios, healthchecks, volúmenes, red, `python:3.12-slim` |
| **Configuración del entorno** | `.env.example` completo, entrypoint idempotente, guía paso a paso |
| **Documentación de implementación** | README 4+1 + `docs/` + Swagger + docstrings |
| **Cobertura de pruebas** | 64 pruebas automatizadas + pruebas de carga concurrentes |
| **Ejecución de pruebas** | `pytest` → 64 passed |
| **Validación de resultados** | Conteos 660/1.320/5/2, health, OpenAPI y build Android |
| **Interfaces** | Panel web mobile-first + app Android + Swagger + Django Admin |
| **Trabajo colaborativo** | Ramas por integrante y comandos documentados en `docs/GUIA_EVIDENCIAS_Y_GIT.md` |

---

## 17. Evidencias y Git

La guía completa de capturas, tabla de evidencias y comandos Git por rama está
en:

**[`docs/GUIA_EVIDENCIAS_Y_GIT.md`](docs/GUIA_EVIDENCIAS_Y_GIT.md)**

Incluye:

- Tabla de capturas para cada `[POR COMPLETAR]` del informe.
- Comandos para las ramas de **Heiner Sepúlveda**, **Vicente Macaya** y
  **Félix Escobar**.
- Flujo de Pull Request, protección de `main` y publicación en GitHub.
- Checklist final de entrega.

---

## Créditos

Proyecto académico **CONATACOCH** — Plataforma de Taxis y Colectivos de Chile.
Diseñado bajo el Modelo 4+1, con persistencia poliglota MySQL 8 + MongoDB Atlas,
panel web mobile-first y app Android nativa.
