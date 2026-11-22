# CONATACOCH — Plataforma de Taxis y Colectivos de Chile

> **Fase 1 de 3 — Infraestructura base, persistencia poliglota y carga inicial.**
> Monorepo listo para evolucionar a una plataforma escalable, stateless y
> desplegable con Docker.

![Fase](https://img.shields.io/badge/fase-1%20de%203-2dd4bf)
![Django](https://img.shields.io/badge/Django-5.2-0C4B33)
![DRF](https://img.shields.io/badge/DRF-3.18-A30000)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

---

## Tabla de contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Stack tecnologico](#2-stack-tecnologico)
3. [Estructura del monorepo](#3-estructura-del-monorepo)
4. [Inicio rapido](#4-inicio-rapido)
5. [Credenciales de prueba](#5-credenciales-de-prueba)
6. [Arquitectura — Modelo 4+1](#6-arquitectura--modelo-41)
   - [6.1 Vista Logica](#61-vista-logica)
   - [6.2 Vista de Procesos](#62-vista-de-procesos)
   - [6.3 Vista de Desarrollo](#63-vista-de-desarrollo)
   - [6.4 Vista Fisica](#64-vista-fisica)
   - [6.5 Vista de Escenarios](#65-vista-de-escenarios)
7. [Bases de datos](#7-bases-de-datos)
8. [Carga inicial idempotente](#8-carga-inicial-idempotente)
9. [Escalabilidad horizontal](#9-escalabilidad-horizontal)
10. [Seguridad](#10-seguridad)
11. [API REST](#11-api-rest)
12. [Operacion y troubleshooting](#12-operacion-y-troubleshooting)
13. [Pruebas y validacion](#13-pruebas-y-validacion)
14. [Trazabilidad con la rubrica](#14-trazabilidad-con-la-rubrica)
15. [Roadmap Fases 2 y 3](#15-roadmap-fases-2-y-3)

---

## 1. Resumen ejecutivo

CONATACOCH es la plataforma del gremio de **taxis y colectivos de Chile**. Esta
primera fase entrega la base tecnica sobre la que se construiran la app Android
(conductores y pasajeros), el panel administrativo y los pagos con QR.

**Entregado en Fase 1**

| Componente | Estado |
|---|---|
| Entorno Docker escalable (`python:3.12-slim`) | ✅ `docker-compose.yml` + healthchecks |
| Backend stateless Django 5 + DRF + drf-spectacular | ✅ `/api/docs/`, JWT, pool MySQL |
| MySQL 8.0 normalizado en 3FN | ✅ 6 entidades, indices B-Tree, RESTRICT |
| Carga inicial idempotente | ✅ 660 itinerarios, 1.320 paraderos, 5 usuarios demo |
| MongoDB Atlas `telemetria_ubicacion` | ✅ PyMongo pool + indices `2dsphere`, compuesto y TTL |
| Panel web servido por Nginx | ✅ `web-admin/` + reverse proxy `/api` |
| Documentacion Modelo 4+1, escalabilidad y despliegue | ✅ este README + `docs/` |

**Datos oficiales cargados:** 660 itinerarios de la Region Metropolitana,
396 folios unicos, 48 comunas, 617 combinaciones `(folio, nombre_recorrido)` y
660 combinaciones `(folio, nombre_recorrido, tipo_trazado)`.

> **Alcance:** la telemetria se *configura* en Fase 1 (esquema e indices), pero
> el endpoint de ingesta en tiempo real y la app Android pertenecen a la Fase 2.
> El modelo de pagos existe, pero el flujo QR completo pertenece a la Fase 3.

---

## 2. Stack tecnologico

| Capa | Tecnologia | Rol |
|---|---|---|
| Runtime | **Python 3.12** (`python:3.12-slim`) | Base reproducible de la imagen |
| API | **Django 5.2 + Django REST Framework 3.18** | Dominio y API REST |
| Contratos | **drf-spectacular + sidecar** | OpenAPI 3 y Swagger UI local |
| Auth | **djangorestframework-simplejwt** | Access/refresh tokens |
| Driver SQL | **PyMySQL** (puro Python) | Sin toolchain nativo en la imagen |
| RDBMS | **MySQL 8.0** | Consistencia transaccional (3FN) |
| NoSQL | **MongoDB Atlas / 8.0 local** | Telemetria GeoJSON de alta escritura |
| Driver NoSQL | **PyMongo** con `maxPoolSize` | Pool de conexiones documental |
| Servidor | **Gunicorn `gthread`** | Workers + threads, stateless |
| Web | **Nginx 1.27 Alpine** | Estaticos, reverse proxy, DNS dinamico |
| Cifrado | **cryptography (Fernet)** | Secretos OTP reversibles |
| Contenedores | **Docker + Compose v2** | Orquestacion local y despliegue |

---

## 3. Estructura del monorepo

```text
proyecto_conatacoch1/
├── docker-compose.yml               # Servicios de produccion (MySQL, backend, Nginx)
├── docker-compose.dev.yml           # Override local (expone :8000 y DEBUG=True)
├── .env.example                     # Contrato de configuracion (12-factor)
├── .dockerignore / .gitignore
├── recorridos_conatacoch_taxi_colectivo_2.json   # Dataset oficial (660 filas)
├── README.md                        # Este documento
│
├── backend/
│   ├── Dockerfile                   # python:3.12-slim, non-root, read-only
│   ├── entrypoint.sh                # wait DB -> migrate -> seed -> indices -> gunicorn
│   ├── requirements.txt
│   ├── manage.py
│   ├── conatacoch/
│   │   ├── __init__.py              # Shim PyMySQL -> MySQLdb
│   │   ├── settings.py              # 12-factor, JWT, pools, Mongo, logging
│   │   ├── urls.py                  # /api/docs/, /api/token/, admin
│   │   ├── wsgi.py / asgi.py
│   ├── core/
│   │   ├── models.py                # 6 entidades 3FN + indices + constraints
│   │   ├── serializers.py
│   │   ├── views.py                 # salud, metricas, viewsets read-only
│   │   ├── pagination.py
│   │   ├── admin.py
│   │   ├── crypto.py                # Fernet para OTP
│   │   ├── mongo.py                 # Cliente pool + indices + insert GeoJSON
│   │   ├── tests.py                 # 11 pruebas automatizadas
│   │   ├── migrations/0001_initial.py
│   │   └── management/commands/
│   │       ├── wait_for_db.py
│   │       ├── seed_conatacoch.py
│   │       └── init_mongo_indexes.py
│
├── web-admin/
│   ├── index.html                   # Dashboard responsive (sin CDN)
│   ├── nginx.conf                   # Estaticos + proxy /api, /admin, /static
│   └── assets/{styles.css,app.js,favicon.svg}
│
├── docs/
│   ├── arquitectura-4plus1.md       # Decisiones y diagramas extendidos
│   ├── modelo-datos.md              # Diccionario de datos e indices
│   └── despliegue.md                # Runbook de despliegue y produccion
│
└── android-app/
    └── README.md                    # Reservado para Fase 2
```

---

## 4. Inicio rapido

### 4.1 Prerrequisitos

- Docker Engine / Docker Desktop con **Compose v2** (`docker compose version`).
- 4 GB de RAM libres recomendados.
- Opcional: cuenta **MongoDB Atlas** para el camino de produccion.
- Opcional: Python 3.12 si se desea ejecutar sin Docker.

### 4.2 Configuracion

```bash
cp .env.example .env
```

En PowerShell:

```powershell
Copy-Item .env.example .env
```

Generar secretos reales (nunca usar los valores de ejemplo):

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

**Opcion A — demo completa sin Atlas (Mongo local):**

```bash
docker compose --profile mongo-local up -d --build
```

**Opcion B — MongoDB Atlas (recomendada para produccion):**

1. Crear un cluster en [MongoDB Atlas](https://www.mongodb.com/atlas).
2. Crear un usuario de base de datos y habilitar el acceso de red (en
   produccion: VPC peering / PrivateLink, no `0.0.0.0/0`).
3. Copiar la cadena de conexion en `.env`:

```dotenv
MONGO_ATLAS_URI=mongodb+srv://usuario:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

4. Levantar sin el perfil local:

```bash
docker compose up -d --build
```

Al iniciar, el backend ejecuta automaticamente:

```text
wait_for_db -> migrate -> seed_conatacoch -> init_mongo_indexes -> gunicorn
```

> La primera ejecucion puede tardar 1–2 minutos (MySQL + 660 recorridos +
> 1.320 paraderos).

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

El backend **no publica puerto en produccion**: todo entra por Nginx, lo que
permite escalar replicas sin conflictos de puertos.

### 4.5 Modo desarrollo (backend expuesto)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Expone `http://localhost:8000` y activa `DEBUG=True` sin montar codigo fuente
(la imagen sigue siendo stateless y `read_only`).

---

## 5. Credenciales de prueba

Creadas por `seed_conatacoch` con hashing PBKDF2 de Django.

| Rol | RUT | Email | Password | Folio | Patente |
|---|---|---|---|---|---|
| **ADMIN** | `11.111.111-1` | `admin@conatacoch.cl` | `AdminConata2026!` | — | — |
| **CONDUCTOR** | `22.222.222-2` | `conductor1@conatacoch.cl` | `Conduc2026!` | `234001` | `ABCD-12` |
| **CONDUCTOR** | `33.333.333-3` | `conductor2@conatacoch.cl` | `Conduc2026!` | `236001` | `EFGH-34` |
| **CLIENTE** | `44.444.444-4` | `pasajero1@conatacoch.cl` | `Pasajero2026!` | — | — |
| **CLIENTE** | `55.555.555-5` | `pasajero2@conatacoch.cl` | `Pasajero2026!` | — | — |

> ⚠️ **Solo demo.** Cambiar obligatoriamente antes de produccion. Los RUT y
> passwords son los exigidos por la especificacion de la Fase 1; el validador
> de formularios exige 12 caracteres, por lo que estas claves demo se cargan
> por comando (bypass controlado) y deben rotarse.

---

## 6. Arquitectura — Modelo 4+1

El diseno sigue **Kruchten (1995)**: cuatro vistas de soporte (Logica,
Procesos, Desarrollo, Fisica) y una vista de Escenarios que las valida.

### 6.1 Vista Logica

Describe **que** hace el sistema y como se descompone en capas y modulos.

```mermaid
flowchart LR
    subgraph Presentacion["Presentacion"]
        WEB["web-admin<br/>Nginx + HTML/CSS/JS"]
        AND["android-app<br/>(Fase 2)"]
    end

    subgraph Aplicacion["Aplicacion"]
        NGX["Nginx<br/>reverse proxy"]
        API["Django 5 + DRF"]
        JWT["SimpleJWT<br/>access / refresh"]
        OAS["drf-spectacular<br/>OpenAPI 3"]
    end

    subgraph Dominio["Dominio CONATACOCH"]
        MOD["Modelos 3FN<br/>Usuario, Linea, Vehiculo,<br/>Conductor, Paradero, Pago"]
        SEED["seed_conatacoch"]
        SEC["Validadores RUT/patente<br/>OTP Fernet / token hash"]
    end

    subgraph Datos["Persistencia poliglota"]
        MYSQL[("MySQL 8<br/>conatacoch")]
        MONGO[("MongoDB Atlas<br/>telemetria_ubicacion")]
    end

    WEB --> NGX --> API
    AND -.-> NGX
    API --> JWT
    API --> OAS
    API --> MOD
    MOD --> MYSQL
    SEED --> MYSQL
    API --> SEC
    API -->|"pool PyMongo"| MONGO
```

| Capa | Modulos | Responsabilidad |
|---|---|---|
| Presentacion | `web-admin/`, `android-app/` (F2) | Dashboard Nginx y clientes |
| Borde | `web-admin/nginx.conf` | TLS termination (externo), estaticos, proxy |
| Aplicacion | `core/views.py`, `serializers.py`, `urls.py` | Contratos REST, permisos, paginacion |
| Seguridad | `settings.py`, `crypto.py` | JWT, throttling, cifrado OTP, headers |
| Dominio | `core/models.py` | Entidades, reglas, constraints, indices |
| Datos | MySQL + `mongo.py` | Transacciones 3FN y telemetria GeoJSON |
| Operacion | `entrypoint.sh`, comandos | Migracion, seed, indices, health |

**Decisiones clave**

- **Usuario unico con discriminador `rol`** en lugar de tablas separadas por
  rol: evita duplicacion de credenciales y mantiene una sola identidad.
- **`LineaColectiva`** modela el itinerario como entidad; la clave natural es
  `(folio, nombre_recorrido, tipo_trazado)` porque el dataset repite folios y
  pares folio/nombre.
- **`Conductor.folio_conatacoch`** es un dato operativo del turno (puede diferir
  del folio asignado al vehiculo en relevos), por lo que no es redundante.
- **`TransaccionPago`** referencia lineas y conductor con `PROTECT` para
  preservar trazabilidad financiera.
- **MongoDB** no reemplaza a MySQL: se usa solo para telemetria de alta
  escritura con patron *write-heavy, read-latest*, TTL y consultas geoespaciales.

### 6.2 Vista de Procesos

Describe **como** fluyen los procesos concurrentes y de arranque.

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

**Solicitud HTTP tipica:**

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

**Procesos concurrentes y garantias**

| Proceso | Concurrencia | Garantia |
|---|---|---|
| API de lectura | Workers/threads Gunicorn | Sin estado compartido; cualquier replica responde |
| Seed | `transaction.atomic()` al arrancar | Todo o nada; `update_or_create` evita duplicados |
| Migraciones | Un solo contenedor al inicio | Idempotentes; en multi-replica usar job aparte |
| Indices Mongo | Idempotentes (`create_index`) | Seguro reejecutar; TTL 14400 s |
| Pago (Fase 3) | Transaccion + RESTRICT | No se borran referencias financieras |
| Telemetria (Fase 2) | Inserción append-only | TTL elimina documentos > 4 h |

**Estado y sesiones:** las sesiones viven en MySQL
(`django.contrib.sessions.backends.db`), la autenticacion API es JWT y no hay
archivos locales. Esto habilita escalado horizontal sin *sticky sessions*.

### 6.3 Vista de Desarrollo

Describe la organizacion del equipo, el monorepo y el flujo de trabajo.

| Area | Responsable | Artefactos |
|---|---|---|
| Infraestructura | DevOps / Cloud | Compose, Dockerfile, `.env`, redes, volumenes |
| Backend / datos | Full-stack / Data | `core/`, migraciones, seed, indices Mongo |
| Frontend admin | Frontend | `web-admin/` |
| Mobile | Android | `android-app/` (Fase 2) |
| Calidad | QA | `core/tests.py`, smoke tests, OpenAPI |

**Convenciones**

- Dominio en espanol (`LineaColectiva`, `Paradero`); framework en ingles.
- Configuracion **solo** por variables de entorno (12-factor).
- Cambios de esquema siempre via migraciones versionadas.
- Serializers de solo lectura en Fase 1 para no exponer escritura sin reglas.
- Secretos nunca en Git (`.env` ignorado; `.env.example` documenta el contrato).
- Imagen inmutable: sin bind mounts de codigo en produccion.

**Flujo para agregar una entidad**

```bash
# 1. Editar backend/core/models.py
# 2. Migracion
docker compose exec backend python manage.py makemigrations core
docker compose exec backend python manage.py migrate
# 3. Serializer + ViewSet + router
# 4. Pruebas
docker compose exec backend python manage.py test core
# 5. Documentacion automatica en /api/docs/
```

**Ejecucion local sin Docker (util para pruebas)**

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
python manage.py runserver
```

Con `DEBUG=True` los estaticos de Swagger y del admin se sirven con
*finders* de Whitenoise, sin necesidad de `collectstatic`.

### 6.4 Vista Fisica

Describe el despliegue, nodos, contenedores, redes y volumenes.

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
    NGX -->|"proxy /api /admin /static"| BE1
    NGX --> BE2
    BE1 --> DB
    BE2 --> DB
    BE1 -.->|"solo si MONGO_ATLAS_URI vacio"| ML
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

**Topologia de produccion recomendada**

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
- El backend puede correr en varias replicas porque no escribe estado local.
- Los volumenes solo almacenan MySQL/Mongo local; el backend no persiste nada.

### 6.5 Vista de Escenarios

Valida que las otras cuatro vistas cubren los casos de uso reales.

| # | Escenario | Actores | Flujo resumido | Componentes |
|---|---|---|---|---|
| E1 | Administrador consulta recorridos | Admin | Login JWT → panel → filtro comuna | Nginx, DRF, MySQL |
| E2 | Pasajero busca un colectivo | Pasajero | Abre panel/API → filtra origen/destino | Nginx, DRF, MySQL |
| E3 | Conductor inicia turno (F2) | Conductor | Login → estado `en_turno` → telemetria | DRF, MySQL, Atlas |
| E4 | Pago con QR (F3) | Pasajero + conductor | Genera UUID → valida → registra pago | DRF, MySQL, JWT |
| E5 | Operador revisa salud | DevOps | `/api/health/` → MySQL + Mongo | Nginx, DRF, Atlas |
| E6 | Arranque/recuperacion | DevOps | Compose levanta → migrate + seed | Docker, MySQL |

**Escenario E2 — busqueda publica (implementado):**

```mermaid
sequenceDiagram
    autonumber
    participant P as Pasajero
    participant W as Panel web
    participant A as API /api/lineas
    participant D as MySQL

    P->>W: escribe "Melipilla"
    W->>A: GET /api/lineas/?search=Melipilla&page_size=25
    A->>D: full-text LIKE + indices de comuna
    D-->>A: resultados paginados
    A-->>W: JSON
    W-->>P: tabla de recorridos y tarifas
```

**Escenario E3 — telemetria (preparado, Fase 2):** el documento ya esta
definido y los indices existen; falta exponer el endpoint de ingesta y el
consumo en tiempo real.

---

## 7. Bases de datos

### 7.1 MySQL 8.0 — modelo relacional en 3FN

Base: `conatacoch`, charset `utf8mb4`, collation `utf8mb4_0900_ai_ci`.

| Entidad | PK | Atributos principales | Claves / indices |
|---|---|---|---|
| `usuario` | `id` | rut, nombre, email, password_hash, rol, activo, intentos_fallidos, bloqueado_hasta | `rut` UNIQUE, `email` UNIQUE, `rol+activo`, `bloqueado_hasta` |
| `linea_colectiva` | `id` | region, folio, tipo_servicio, nombre_recorrido, tipo_trazado, origen/destino, tarifa_actual | `folio` INDEX, `(folio,nombre_recorrido,tipo_trazado)` UNIQUE, `(region,folio)`, comunas |
| `vehiculo` | `id` | patente, marca_modelo, capacidad_pasajeros, linea_id | `patente` UNIQUE, `linea` INDEX |
| `conductor` | `id` | usuario_id, folio_conatacoch, vehiculo_id, en_turno, cupos_disponibles, otp_secreto, token_sesion_activa | `folio_conatacoch`, `(en_turno,folio)`, `(vehiculo,en_turno)` |
| `paradero` | `id` | nombre, comuna, latitud, longitud, linea_id | `(linea,nombre)` UNIQUE, `(comuna,linea)`, `(latitud,longitud)` |
| `transaccion_pago` | `id` | codigo_qr_uuid, pasajero_id, conductor_id, linea_id, monto, fecha_hora, estado | `codigo_qr_uuid` UNIQUE, `(conductor,fecha)`, `(linea,fecha)`, `(pasajero,fecha)`, `(estado,fecha)` |

**Justificacion 3FN**

1. **1FN:** todos los atributos son atomicos. No hay listas de paraderos ni
   arreglos embebidos; los paraderos son filas propias con FK.
2. **2FN:** la PK surrogate `id` no genera dependencias parciales; la clave
   natural compuesta se declara como restriccion unica y todos los atributos
   dependen del itinerario completo.
3. **3FN:** no hay dependencias transitivas entre atributos no clave. Comunas,
   origenes y destinos son atributos del recorrido; no se almacena una tabla de
   comunas duplicada ni el nombre de la linea dentro del vehiculo, conductor o
   pago (solo la FK).
4. **Sin redundancia controlada:** `tarifa_actual` es el valor vigente de la
   linea; un historial de tarifas seria una tabla adicional en Fase 3.
5. **Clave natural del dataset:** se verifico que 660 filas producen 617 pares
   `(folio, nombre_recorrido)`; al agregar `tipo_trazado` se obtienen 660
   combinaciones unicas. Por eso la restriccion es triple y no `folio` solo.

**Integridad referencial**

- Todas las FK usan `on_delete=PROTECT` en Django, equivalente ORM a
  `ON DELETE RESTRICT`.
- MySQL/InnoDB aplica **RESTRICT por defecto** a las FK, por lo que el borrado
  de una linea/vehiculo/conductor referenciado falla tambien a nivel de motor.
- Restricciones `CHECK` adicionales: montos y tarifas ≥ 0, capacidades 1–30,
  coordenadas en rango, cupos 0–30, region/folio > 0.

**Indices B-Tree** (nombres reales de la migracion)

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

> Los indices se declaran explicitamente en `Meta.indexes` y las restricciones
> en `Meta.constraints`; no dependen de nombres autogenerados.

### 7.2 Pool de conexiones MySQL

En `settings.py`:

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
Cada thread reutiliza la conexion del worker, reduciendo el costo de handshake
y manteniendo el consumo dentro de `max_connections=300` de MySQL.

### 7.3 MongoDB Atlas — `telemetria_ubicacion`

**Documento GeoJSON** (coleccion `ubicaciones`):

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
  "timestamp": { "$date": "2026-11-21T14:30:00Z" }
}
```

> GeoJSON usa orden **`[longitud, latitud]`**. El timestamp se guarda en UTC.

**Indices creados automaticamente** (`init_mongo_indexes`, idempotente):

| Nombre | Claves | Opcion | Proposito |
|---|---|---|---|
| `idx_ubicacion_2dsphere` | `ubicacion` | `2dsphere` | `$near`, `$geoWithin`, distancia |
| `idx_folio_timestamp` | `folio_linea: 1, timestamp: -1` | — | Ultima posicion por recorrido |
| `idx_timestamp_ttl` | `timestamp: 1` | `expireAfterSeconds: 14400` | Retencion 4 horas |
| `idx_vehiculo_timestamp` | `id_vehiculo: 1, timestamp: -1` | — | Ultima posicion por vehiculo |

**Seleccion del backend:** si `MONGO_ATLAS_URI` tiene valor se usa Atlas con
`tls=True`; si esta vacio se usa `MONGO_LOCAL_URI`
(`mongodb://mongo_local:27017`). El cliente se crea una vez por proceso con
`maxPoolSize=50`, `minPoolSize=5` y `serverSelectionTimeoutMS=5000`.

**Verificar indices:**

```bash
docker compose exec backend python manage.py init_mongo_indexes
# o en mongosh:
use telemetria_ubicacion
db.ubicaciones.getIndexes()
```

> El monitor TTL de MongoDB se ejecuta aproximadamente cada 60 s; la expiracion
> no es exacta al segundo. Si se cambia `MONGO_TTL_SECONDS`, usar `collMod` sobre
> el indice existente (MongoDB no permite recrearlo con otra opcion sin
> conflicto).

---

## 8. Carga inicial idempotente

**Comando:** `python manage.py seed_conatacoch`

Se ejecuta automaticamente si `SEED_ON_START=true` (default). Es seguro
reejecutarlo: usa `update_or_create` con las claves naturales.

| Paso | Resultado |
|---|---|
| Lee `recorridos_conatacoch_taxi_colectivo_2.json` | 660 itinerarios |
| `update_or_create` por `(folio, nombre_recorrido, tipo_trazado)` | 660 lineas |
| Crea paraderos de origen/destino por linea | 1.320 paraderos |
| Crea usuarios, vehiculos y conductores demo | 5 usuarios, 2 vehiculos, 2 conductores |
| Asigna tarifa demo | urbana 1.000 CLP / rural 1.500 CLP |
| Cifra OTP de conductores y deja token vacio | Secretos protegidos |

**Paraderos:** se usa el centroide aproximado de cada comuna de la Region
Metropolitana (mapa de 48 comunas) mas un *jitter* deterministico de ~1 km
derivado de SHA-256. Es data base para desarrollo; en produccion se reemplaza
por geocodificacion real o coordenadas oficiales.

**Opciones utiles**

```bash
python manage.py seed_conatacoch --skip-paraderos
python manage.py seed_conatacoch --skip-usuarios
python manage.py seed_conatacoch --data-file /ruta/otro.json
python manage.py seed_conatacoch --tarifa-urbana 1200 --tarifa-rural 1800
```

**Ubicacion del dataset:** en Docker se copia a
`/app/data/recorridos_conatacoch_taxi_colectivo_2.json` durante el build
(imagen inmutable). Se puede sobreescribir con `SEED_DATA_FILE`.

> Nota: el archivo `recorridos_conatacoch_taxi_colectivo_2.json` se incorporo a
> la raiz del proyecto a partir del dataset oficial disponible en el entorno.

---

## 9. Escalabilidad horizontal

### 9.1 Backend sin estado

| Requisito stateless | Implementacion |
|---|---|
| Sesiones no locales | `SESSION_ENGINE` en MySQL |
| Auth API | JWT firmado; no hay sesion de servidor |
| Archivos subidos | No existen en Fase 1; media iria a S3/Blob en F2 |
| Logs | `stdout` (Docker logging driver) |
| Configuracion | Variables de entorno |
| Filesystem | Contenedor `read_only: true` + `tmpfs /tmp` |
| Seed/migraciones | Al arranque, idempotentes |
| Balanceo | Nginx con `resolver 127.0.0.11` re-resuelve `backend` |

**Escalar:**

```bash
docker compose up -d --scale backend=3
```

Nginx descubre las IPs nuevas via DNS de Docker gracias a:

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
set $backend_upstream http://backend:8000;
proxy_pass $backend_upstream;
```

No se requiere *sticky session* ni afinidad de sesion.

### 9.2 Capacidad de conexiones

```text
conexiones ≈ replicas_backend × GUNICORN_WORKERS × GUNICORN_THREADS
```

| Replicas | Workers | Threads | Conexiones aprox. | MySQL `max_connections=300` |
|---|---|---|---|---|
| 1 | 3 | 4 | 12 | 4 % |
| 3 | 3 | 4 | 36 | 12 % |
| 8 | 3 | 4 | 96 | 32 % |

Dejar al menos 30 % de holgura para migraciones, admin y monitoreo. Si se
supera, aumentar `max_connections` o usar un pooler (ProxySQL) en Fase 2.

### 9.3 Estrategia por capa

| Capa | Ahora (F1) | Siguiente |
|---|---|---|
| Web/API | Nginx + N replicas Gunicorn | HPA/autoescalado, CDN, WAF |
| MySQL | Un primary con indices | Read replicas para reportes, particion de `transaccion_pago` por fecha |
| Mongo | Atlas replica set + TTL | Sharding por `folio_linea`, *time series collection* |
| Cache | Sin cache | Redis para tarifas/recorridos y rate limit distribuido |
| Asincronia | Sin colas | Celery/SQS para pagos, notificaciones y reconciliacion |
| Seed | Al arrancar | Job de despliegue separado en multi-replica |

> El seed y las migraciones deben ejecutarse **una vez** por despliegue
> (job/init container) cuando haya muchas replicas. En Compose de Fase 1 se
> ejecutan en el unico backend; con `--scale backend=N` conviene desactivar
> `SEED_ON_START` y correrlas como paso previo.

---

## 10. Seguridad

| Control | Implementacion |
|---|---|
| Password hashing | PBKDF2-SHA256 de Django (`password_hash`, nunca texto plano) |
| JWT | `HS256` con `JWT_SECRET` independiente de `SECRET_KEY`; access 60 min, refresh 7 dias, rotacion |
| Autorizacion | Lectura publica solo de lineas/paraderos/stats; flota y pagos requieren JWT |
| Throttling | `AnonRateThrottle 60/min`, `UserRateThrottle 600/min` |
| Fuerza bruta | Campos `intentos_fallidos` y `bloqueado_hasta` + metodos de bloqueo |
| RUT / patente | Validadores de digito verificador y formato |
| OTP | Cifrado Fernet (AES + HMAC), columna `otp_secreto` |
| Token de sesion | Solo hash SHA-256 en `token_sesion_activa` |
| Secretos | `.env` fuera de Git; `.env.example` como contrato |
| Contenedor | Usuario `appuser` UID 10001, `read_only`, `tmpfs`, sin privilegios |
| BD expuesta | MySQL solo en red interna en produccion; puerto local desactivable |
| Cabeceras | `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` |
| ORM | Consultas parametrizadas; sin SQL concatenado |
| Documentacion | Swagger self-hosted (sin CDN externo) |

**Checklist antes de produccion**

- [ ] Rotar las 5 passwords demo y eliminar usuarios de prueba.
- [ ] Generar `SECRET_KEY` y `JWT_SECRET` de 64+ caracteres.
- [ ] `DEBUG=False`, `SECURE_SSL_REDIRECT=True`, cookies `Secure`.
- [ ] TLS en el load balancer y `CSRF_TRUSTED_ORIGINS` con el dominio real.
- [ ] Eliminar la publicacion del puerto 3306 de `db_mysql`.
- [ ] Restringir Atlas por IP/VPC y usar usuario con privilegios minimos.
- [ ] Configurar backups de MySQL y snapshots de Atlas.
- [ ] Centralizar logs y alertas de `/api/health/`.

> Nota: `ROTATE_REFRESH_TOKENS=True` pero `BLACKLIST_AFTER_ROTATION=False`
> porque la app de blacklist no se instala en Fase 1. En Fase 2 se agrega
> `rest_framework_simplejwt.token_blacklist` para revocacion inmediata.

---

## 11. API REST

Documentacion interactiva: **`/api/docs/`** (Swagger) y **`/api/redoc/`**.
Esquema: **`/api/schema/`** (OpenAPI 3).

| Metodo | Endpoint | Auth | Descripcion |
|---|---|---|---|
| GET | `/api/health/live/` | Publico | Liveness |
| GET | `/api/health/` | Publico | Readiness MySQL + Mongo |
| GET | `/api/stats/` | Publico | Agregados para el panel |
| GET | `/api/lineas/` | Publico | Recorridos; filtros `comuna`, `folio`, `region`, `tipo_servicio`, `search` |
| GET | `/api/lineas/{id}/` | Publico | Detalle de recorrido |
| GET | `/api/paraderos/` | Publico | Filtros `comuna`, `linea` |
| GET | `/api/vehiculos/` | JWT | Flota; filtro `linea` |
| GET | `/api/conductores/` | JWT | Conductores; filtros `en_turno`, `folio` |
| GET | `/api/transacciones/` | JWT | Pagos; filtros `estado`, `conductor`, `linea`, `pasajero`, `desde`, `hasta` |
| POST | `/api/token/` | Publico | Obtener access + refresh |
| POST | `/api/token/refresh/` | Publico | Renovar access |
| POST | `/api/token/verify/` | Publico | Verificar token |
| GET | `/api/docs/` | Publico | Swagger UI |
| GET | `/admin/` | Staff | Django Admin |

### Ejemplo de autenticacion

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@conatacoch.cl","password":"AdminConata2026!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s http://localhost:8080/api/conductores/ \
  -H "Authorization: Bearer $TOKEN"
```

PowerShell:

```powershell
$body = @{ email="admin@conatacoch.cl"; password="AdminConata2026!" } | ConvertTo-Json
$token = (Invoke-RestMethod -Method Post -Uri "http://localhost:8080/api/token/" `
  -ContentType "application/json" -Body $body).access
Invoke-RestMethod -Uri "http://localhost:8080/api/conductores/" `
  -Headers @{ Authorization = "Bearer $token" }
```

### Paginacion

`?page=2&page_size=50` (maximo 100). Respuesta estandar DRF:
`count`, `next`, `previous`, `results`.

### Ejemplo de health

```json
{
  "status": "ok",
  "service": "conatacoch-backend",
  "version": "1.0.0-fase1",
  "components": {
    "mysql": { "status": "ok", "latency_ms": 1.42, "database": "conatacoch" },
    "mongodb": { "status": "ok", "latency_ms": 35.1, "mode": "atlas",
                 "database": "telemetria_ubicacion" }
  }
}
```

Si Atlas no responde, `status` es `degraded` y el HTTP sigue en 200 para no
matar el servicio por una dependencia no critica de Fase 1.

---

## 12. Operacion y troubleshooting

### Comandos utiles

```bash
docker compose ps
docker compose logs -f backend
docker compose exec backend python manage.py seed_conatacoch
docker compose exec backend python manage.py init_mongo_indexes
docker compose exec backend python manage.py test core
docker compose exec db_mysql mysql -uconatacoch -p conatacoch -e "SHOW TABLES;"
docker compose --profile mongo-local exec mongo_local mongosh
```

### Reinicio limpio (destructivo)

```bash
docker compose down -v
docker compose --profile mongo-local up -d --build
```

`-v` elimina los volumenes `conatacoch_mysql_data` y
`conatacoch_mongo_data`. No usar en produccion.

### Problemas frecuentes

| Sintoma | Causa probable | Solucion |
|---|---|---|
| Panel muestra MongoDB `degraded` | Atlas vacio y perfil local no iniciado | Configurar `MONGO_ATLAS_URI` o usar `--profile mongo-local` |
| `502 Bad Gateway` en panel | Backend aun arrancando/migrando | `docker compose logs -f backend`, esperar healthcheck |
| `port is already allocated` | Puerto 8080/3306 ocupado | Cambiar `WEB_ADMIN_PORT`/`MYSQL_EXPOSED_PORT` en `.env` |
| Backend reinicia en loop | Credenciales MySQL incorrectas o DB no lista | Revisar `.env`, `docker compose logs db_mysql` |
| `/api/docs/` sin estilos | Falta `collectstatic` en imagen | Reconstruir (`--build`); en local usar `DEBUG=True` |
| Acentos rotos | Cliente sin UTF-8 | MySQL ya usa `utf8mb4`; revisar terminal/cliente |
| TTL no borra documentos | Monitor TTL corre cada ~60 s o indice ausente | Ejecutar `init_mongo_indexes`; esperar |
| Seed lento en MySQL | 660 lineas + 1.320 paraderos | Normal en primer arranque; usar `--skip-paraderos` en pruebas |

### Backups

```bash
# MySQL
docker compose exec db_mysql mysqldump -uconatacoch -p conatacoch > backup.sql

# Atlas: snapshots continuos del cluster gestionado (consola/Atlas CLI)
```

---

## 13. Pruebas y validacion

Suite: `backend/core/tests.py` (11 pruebas).

```bash
docker compose exec backend python manage.py test core
```

Resultado de la validacion ejecutada en esta entrega (Python 3.12 + SQLite):

```text
Ran 11 tests in 7.799s
OK
```

Cobertura:

- Seed completo y **segunda ejecucion idempotente** (660 lineas, 0 duplicados).
- 5 usuarios, 2 vehiculos, 2 conductores; passwords verificados.
- OTP descifrable y token de sesion vacio/hasheado.
- RUT invalido rechazado.
- `PROTECT` impide borrar una linea referenciada.
- Health publico y `degraded` cuando Mongo no responde.
- Stats publicas (660 lineas, 396 folios, 48 comunas).
- Filtro publico de recorridos y paginacion.
- Flota protegida por JWT (401 sin token, 200 con token).
- Secretos no expuestos en el serializer de conductores.
- OpenAPI y Swagger responden 200.

Validacion adicional ejecutada:

```text
manage.py check                              -> 0 issues
manage.py makemigrations --check             -> sin cambios pendientes
manage.py spectacular --validate             -> schema valido
manage.py collectstatic --noinput            -> 655 archivos
docker-compose.yml (YAML)                    -> parseo correcto, 4 servicios
admin (login + listados)                     -> 302 a /admin/ y paginas 200
```

> **Nota de validacion:** el entorno donde se preparo esta entrega no dispone de
> Docker, por lo que `docker-compose.yml` se valido como YAML y sus servicios se
> revisaron estaticamente, pero **no se ejecuto `docker compose up` aqui**. En
> la maquina destino ejecutar el inicio rapido de la seccion 4 y el checklist de
> la seccion 6 de `docs/despliegue.md`.

---

## 14. Trazabilidad con la rubrica

| Criterio | Evidencia |
|---|---|
| **Estructura adecuada de la BD** | 6 entidades normalizadas, FK, `CHECK`, migracion versionada |
| **Optimizacion y normalizacion (3FN)** | Justificacion 3FN, indices B-Tree compuestos, clave natural validada |
| **Bases de datos en la nube** | MongoDB Atlas con TLS, pool PyMongo, `2dsphere`, TTL 4 h |
| **Patrones de seguridad** | JWT, PBKDF2, throttling, Fernet, hash de token, contenedor non-root/read-only |
| **Entorno Docker** | Compose con 4 servicios, healthchecks, volumenes, red, `python:3.12-slim` |
| **Configuracion del entorno** | `.env.example` completo, entrypoint idempotente, guia paso a paso |
| **Documentacion de implementacion** | README 4+1 + `docs/` + Swagger + docstrings |
| **Cobertura de pruebas** | 11 pruebas automatizadas + smoke test de seed/JWT |
| **Ejecucion de pruebas** | `manage.py test core` => OK |
| **Validacion de resultados** | Conteos 660/1.320/5/2, health y OpenAPI verificados |
| **Interfaces** | Panel responsive + Swagger + Django Admin |

---

## 15. Roadmap Fases 2 y 3

**Fase 2 — Operacion en tiempo real**

- App Android para conductores y pasajeros.
- Endpoint `POST /api/telemetria/` con validacion y escritura en Mongo.
- WebSocket/SSE para mapa de vehiculos y cupos en vivo.
- Turnos, cupos y bloqueo por intentos conectados al login real.
- Redis para cache y throttling distribuido.

**Fase 3 — Pagos y analitica**

- Generacion y validacion de QR con `codigo_qr_uuid`.
- Conciliacion de pagos, reembolsos y estados.
- Reporteria por linea/conductor y tableros analiticos.
- Particionamiento/tablas historicas y read replicas.
- Observabilidad (Prometheus/Grafana, trazas) y CI/CD completo.

---

## Creditos

Proyecto academico **CONATACOCH** — Plataforma de Taxis y Colectivos de Chile.
Disenado bajo el Modelo 4+1, con persistencia poliglota MySQL 8 + MongoDB
Atlas y despliegue Docker reproducible.
