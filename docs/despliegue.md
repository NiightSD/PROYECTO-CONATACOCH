# Guia de despliegue CONATACOCH — Fase 1

Runbook para levantar, verificar y operar la plataforma en local, demo y
produccion.

---

## 1. Ambientes

| Ambiente | Datos | Mongo | Objetivo |
|---|---|---|---|
| Local dev | Seed completo | `mongo_local` o Atlas | Desarrollo y pruebas |
| Demo/evaluacion | Seed completo | `mongo_local` (offline) | Mostrar la entrega |
| Staging | Seed + datos sinteticos | Atlas dedicado | Validar despliegue |
| Produccion | Datos reales | Atlas con backup | Operacion |

---

## 2. Prerrequisitos

| Herramienta | Version minima | Verificar |
|---|---|---|
| Docker Engine / Desktop | 24+ | `docker --version` |
| Docker Compose | v2.24+ | `docker compose version` |
| Python (solo local) | 3.12 | `python --version` |
| Cuenta MongoDB Atlas | Free/M10+ | Consola web |

Recursos recomendados: 2 vCPU, 4 GB RAM, 10 GB libres.

---

## 3. Configuracion del entorno

```bash
cp .env.example .env
```

### 3.1 Variables principales

| Variable | Default | Obligatoria | Descripcion |
|---|---|---|---|
| `SECRET_KEY` | insegura | Si | Firma Django; generar 64+ chars |
| `JWT_SECRET` | insegura | Si | Firma JWT; independiente |
| `DEBUG` | `False` | Si | Nunca `True` en produccion |
| `ALLOWED_HOSTS` | localhost,... | Si | Dominios separados por coma |
| `CSRF_TRUSTED_ORIGINS` | localhost | Si | Incluir esquema `https://` |
| `MYSQL_ROOT_PASSWORD` | demo | Si | Password root MySQL |
| `MYSQL_DATABASE` | `conatacoch` | Si | Base |
| `MYSQL_USER` | `conatacoch` | Si | Usuario app |
| `MYSQL_PASSWORD` | demo | Si | Password app |
| `MYSQL_EXPOSED_PORT` | `3306` | No | Puerto host (eliminar en prod) |
| `DB_CONN_MAX_AGE` | `600` | No | Reutilizacion de conexiones |
| `ACCESS_TOKEN_MINUTES` | `60` | No | Vigencia del access token |
| `REFRESH_TOKEN_DAYS` | `7` | No | Vigencia del refresh token |
| `OTP_ENCRYPTION_KEY` | vacio | No | Clave Fernet dedicada para OTP (si falta, deriva de `SECRET_KEY`) |
| `SECURE_SSL_REDIRECT` | `False` | No | Forzar HTTPS (activar tras TLS) |
| `SESSION_COOKIE_SECURE` | `False` | No | Cookie de sesion solo HTTPS |
| `CSRF_COOKIE_SECURE` | `False` | No | Cookie CSRF solo HTTPS |
| `SECURE_HSTS_SECONDS` | `0` | No | HSTS (activar con TLS estable) |
| `THROTTLE_ANON` | `60/min` | No | Limite de peticiones anonimas |
| `THROTTLE_USER` | `600/min` | No | Limite de peticiones autenticadas |
| `LOG_LEVEL` | `INFO` | No | Nivel de logging de la app |
| `MONGO_ATLAS_URI` | vacio | No | Si existe, prioridad Atlas + TLS |
| `MONGO_LOCAL_URI` | `mongodb://mongo_local:27017` | No | Fallback |
| `MONGO_DB_NAME` | `telemetria_ubicacion` | No | Base documental |
| `MONGO_COLLECTION` | `ubicaciones` | No | Coleccion |
| `MONGO_TTL_SECONDS` | `14400` | No | Retencion telemetria |
| `SEED_ON_START` | `true` | No | Carga inicial automatica |
| `WEB_ADMIN_PORT` | `8080` | No | Puerto publico del panel |
| `GUNICORN_WORKERS` | `3` | No | Workers por replica |
| `GUNICORN_THREADS` | `4` | No | Threads por worker |

Generar secretos:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3.2 Ejemplo minimo para demo

```dotenv
SECRET_KEY=<generado>
JWT_SECRET=<generado>
MYSQL_ROOT_PASSWORD=RootDemo2026!
MYSQL_PASSWORD=ConataDemo2026!
MONGO_ATLAS_URI=
WEB_ADMIN_PORT=8080
```

---

## 4. MongoDB Atlas paso a paso

1. **Crear cuenta/proyecto** en <https://cloud.mongodb.com>.
2. **Create Cluster** → proveedor/region cercana (por ejemplo AWS
   `us-east-1` o GCP `southamerica-east1`).
3. **Database Access** → Add New Database User:
   - Rol: `readWrite` sobre `telemetria_ubicacion`.
   - Password fuerte, guardarla en un gestor de secretos.
4. **Network Access**:
   - Demo: IP publica del host (`/32`).
   - Produccion: VPC peering, PrivateLink o rango privado; nunca `0.0.0.0/0`.
5. **Connect → Drivers → Python** → copiar URI:

```text
mongodb+srv://conatacoch_app:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

6. Si el password contiene `@`, `:`, `/`, codificarlo con URL encoding.
7. Pegar en `.env`:

```dotenv
MONGO_ATLAS_URI=mongodb+srv://...
```

8. Levantar:

```bash
docker compose up -d --build
```

9. Verificar indices:

```bash
docker compose exec backend python manage.py init_mongo_indexes
docker compose logs backend | grep mongo
```

Salida esperada:

```text
[mongo] Destino=Atlas db=telemetria_ubicacion coleccion=ubicaciones ttl=14400s
[mongo] Indice listo: idx_ubicacion_2dsphere (geo)
[mongo] Indice listo: idx_folio_timestamp (folio_timestamp)
[mongo] Indice listo: idx_timestamp_ttl (ttl)
[mongo] Indice listo: idx_vehiculo_timestamp (vehiculo_timestamp)
```

10. En `mongosh`:

```javascript
use telemetria_ubicacion
db.ubicaciones.getIndexes()
```

**Nota TTL:** si ya existe `idx_timestamp_ttl` con otro valor, MongoDB puede
rechazar la recreacion. Ajustar con:

```javascript
db.runCommand({
  collMod: "ubicaciones",
  index: { name: "idx_timestamp_ttl", expireAfterSeconds: 14400 }
});
```

---

## 5. Levantar el entorno

### 5.1 Demo con Mongo local

```bash
docker compose --profile mongo-local up -d --build
```

### 5.2 Con Atlas

```bash
docker compose up -d --build
```

### 5.3 Desarrollo con backend expuesto

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 5.4 Espera de arranque

```bash
docker compose ps
docker compose logs -f backend
```

Secuencia esperada:

```text
[entrypoint] Iniciando CONATACOCH backend...
[wait_for_db] MySQL disponible
Applying migrations... OK
[seed] ... 660 itinerarios
[seed] Completado ... (idempotente)
[mongo] Indice listo: ...
[gunicorn] Listening at: http://0.0.0.0:8000
```

---

## 6. Verificacion

| Paso | Comando | Esperado |
|---|---|---|
| Contenedores | `docker compose ps` | `healthy` en MySQL/Nginx/backend |
| Liveness | `curl http://localhost:8080/api/health/live/` | 200 `ok` |
| Readiness | `curl http://localhost:8080/api/health/` | 200 `ok` (o `degraded` sin Mongo) |
| Stats | `curl http://localhost:8080/api/stats/` | `lineas=660` |
| Recorridos | `curl "http://localhost:8080/api/lineas/?page_size=1"` | JSON paginado |
| Swagger | abrir `http://localhost:8080/api/docs/` | UI interactiva |
| Admin | abrir `http://localhost:8080/admin/` | Login con admin demo |
| MySQL | `docker compose exec db_mysql mysql -uconatacoch -p -e "USE conatacoch; SHOW TABLES;"` | 6 tablas de dominio |
| Mongo | `docker compose exec backend python manage.py init_mongo_indexes` | 4 indices |

Prueba JWT:

```bash
curl -s -X POST http://localhost:8080/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@conatacoch.cl","password":"AdminConata2026!"}'
```

---

## 7. Carga inicial y reset

```bash
# Carga manual (idempotente)
docker compose exec backend python manage.py seed_conatacoch

# Solo lineas, sin paraderos
docker compose exec backend python manage.py seed_conatacoch --skip-paraderos

# Recrear todo desde cero (DESTRUCTIVO)
docker compose down -v
docker compose --profile mongo-local up -d --build
```

**Cuando desactivar el seed automatico:** en staging/produccion con varias
replicas o datos reales, usar `SEED_ON_START=false` y ejecutar la carga como
job controlado una sola vez.

---

## 8. Escalabilidad

### 8.1 Escalar el backend

```bash
docker compose up -d --scale backend=3
docker compose ps
```

Nginx re-resuelve `backend` cada 10 s:

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
set $backend_upstream http://backend:8000;
proxy_pass $backend_upstream;
```

Requisitos para que funcione:

- No publicar el puerto 8000 del backend (el compose base no lo hace).
- No usar `container_name` fijo (el compose no lo usa).
- `SEED_ON_START=false` en despliegues multi-replica.
- Migraciones como job previo.

### 8.2 Dimensionar conexiones

```text
conexiones ≈ replicas × workers × threads
```

Ejemplo: 3 réplicas × 3 workers × 4 threads = 36 conexiones. MySQL permite 300.
Mantener 30 % de holgura.

### 8.3 Cuellos de botella esperados

| Capa | Limite | Mitigacion |
|---|---|---|
| MySQL escrituras | Un primary | Particionar pagos, job batch |
| MySQL lecturas | Conexiones/IO | Read replica, indices, cache |
| Mongo escrituras | Throughput del cluster | Sharding por `folio_linea` |
| Nginx DNS | Round-robin sin health-check | LB externo con health checks |
| Seed | Bloquea arranque | Job separado / `--skip-paraderos` |

---

## 9. Endurecimiento de produccion

### 9.1 Checklist obligatorio

- [ ] `DEBUG=False`.
- [ ] `SECRET_KEY` y `JWT_SECRET` de 64+ caracteres, en gestor de secretos.
- [ ] `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con el dominio real.
- [ ] TLS terminado en LB/Ingress; `SECURE_SSL_REDIRECT=True`,
      `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, HSTS.
- [ ] Eliminar `ports` de `db_mysql` y `mongo_local`.
- [ ] Rotar/eliminar las 5 credenciales demo.
- [ ] Atlas con IP/VPC allowlist y backups.
- [ ] Backups MySQL programados y probados.
- [ ] Limites de recursos (`deploy.resources` o Kubernetes).
- [ ] Logs centralizados y alertas de health.
- [ ] `SEED_ON_START=false` + job inicial.
- [ ] Monitoreo de disco/volumen MySQL.

### 9.2 TLS con reverse proxy

Agregar un servicio Caddy/Traefik delante de `web_admin` (o usar el LB del
cloud). Ejemplo conceptual con Caddy:

```caddyfile
admin.conatacoch.cl {
    encode gzip
    reverse_proxy web_admin:80
}
```

`web_admin` no debe publicar `:8080` al exterior; solo el proxy TLS.

### 9.3 Secretos

- Docker Compose local: `.env` (permisos restringidos).
- Produccion: AWS Secrets Manager, GCP Secret Manager, Azure Key Vault o
  Kubernetes Secrets cifrados.
- No pasar secretos por `docker build` (quedan en capas).
- Rotar `JWT_SECRET` invalida todos los tokens vigentes: coordinar ventana.
- Rotar `SECRET_KEY` invalida sesiones y descifrado OTP; migrar secretos OTP a
  KMS antes de rotar.

### 9.4 Backups y restauracion

**MySQL**

```bash
docker compose exec db_mysql sh -c \
  'mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' > backup.sql

# Restaurar
docker compose exec -T db_mysql sh -c \
  'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' < backup.sql
```

Programar con cron/servicio externo, cifrar y probar restauracion.

**Atlas**

- Snapshots continuos incluidos en clusters dedicados.
- Exportar a S3 con `mongodump` si se requiere retencion extendida.
- La telemetria tiene TTL 4 h: no es un dato de respaldo por diseno.

---

## 10. Observabilidad

| Senal | Fuente | Accion |
|---|---|---|
| Liveness | `/api/health/live/` | Reiniciar si falla 3 veces |
| Readiness | `/api/health/` | Degradar trafico si MySQL falla |
| Latencia MySQL/Mongo | health JSON | Alerta > 200 ms sostenido |
| Logs | stdout Docker | Centralizar (Loki/CloudWatch) |
| Errores 5xx | Nginx logs | Alerta |
| Espacio disco | host | Alerta > 80 % |

Comandos:

```bash
docker compose logs -f --tail=200 backend
docker stats
```

---

## 11. CI/CD sugerido

```yaml
# Pseudocodigo de pipeline
stages:
  - lint:      ruff check backend
  - test:      python manage.py test core (SQLite o MySQL service)
  - schema:    python manage.py spectacular --validate
  - build:     docker build -f backend/Dockerfile -t registry/conatacoch-backend:$SHA .
  - migrate:   job unico con la imagen nueva
  - deploy:    rolling update de backend + web_admin
  - smoke:     curl /api/health/live/ y /api/stats/
```

Buenas practicas:

- Etiquetar imagenes por commit, no `latest` en produccion.
- Migraciones antes del rolling update.
- Rollback: desplegar la imagen anterior; las migraciones deben ser
  compatibles hacia atras.
- Escanear imagen (Trivy) y dependencias (pip-audit).

---

## 12. Troubleshooting expandido

| Error | Diagnostico | Solucion |
|---|---|---|
| `Access denied for user 'conatacoch'` | Password distinto entre `.env` y volumen existente | Mantener password o borrar volumen `conatacoch_mysql_data` (destructivo) |
| `Unknown database 'conatacoch'` | MySQL no inicializo | Revisar `MYSQL_DATABASE`; recrear volumen |
| `Can't connect to MySQL` en entrypoint | DB aun arrancando | Aumentar `DB_WAIT_RETRIES`; revisar health |
| `502` en Nginx | Backend caido o migrando | `docker compose logs backend`; esperar |
| `degraded` MongoDB | URI vacia y sin perfil | Usar `--profile mongo-local` o configurar Atlas |
| `ServerSelectionTimeoutError` | IP no autorizada / TLS | Revisar Network Access y URI |
| `IndexOptionsConflict` | TTL distinto al existente | `collMod` o borrar indice y recrear |
| `Missing staticfiles manifest` | Imagen sin `collectstatic` | Reconstruir imagen; no borrar `staticfiles` del build |
| `CSRF verification failed` | Origen no confiable | Agregar dominio a `CSRF_TRUSTED_ORIGINS` |
| `401` inesperado | Token expirado | Renovar con `/api/token/refresh/` |
| `port is already allocated` | Puerto ocupado | Cambiar `WEB_ADMIN_PORT`/`MYSQL_EXPOSED_PORT` |
| Seed lento | 660 lineas + 1.320 paraderos | Usar `--skip-paraderos` o job batch |
| Acentos incorrectos | Cliente no UTF-8 | MySQL usa `utf8mb4`; configurar terminal |

### Verificacion de conectividad interna

```bash
docker compose exec backend python -c "import socket; print(socket.gethostbyname('db_mysql'))"
docker compose exec backend python -c "import socket; print(socket.gethostbyname('mongo_local'))"
docker compose exec web_admin wget -qO- http://backend:8000/api/health/live/
```

---

## 13. Rollback

1. Detener el backend nuevo.
2. Volver a la imagen etiquetada anterior.
3. Si la migracion es incompatible, restaurar el backup previo (no usar
   `migrate core zero` en produccion).
4. Verificar `/api/health/`, `/api/stats/` y el panel.

---

## 14. Checklist de aceptacion Fase 1

- [x] `docker-compose.yml` con MySQL, backend, Nginx y Mongo local opcional.
- [x] MySQL 8 con volumen persistente y healthcheck.
- [x] Backend `python:3.12-slim` + Django + DRF + spectacular en `/api/docs/`.
- [x] Backend stateless con pool de conexiones.
- [x] `.env.example` con MySQL, `SECRET_KEY`, `JWT_SECRET`, `MONGO_ATLAS_URI`.
- [x] Fallback Mongo local solo si Atlas esta vacio.
- [x] Modelo 3FN con indices B-Tree y `PROTECT/RESTRICT`.
- [x] Seed idempotente con 660 rutas y paraderos RM.
- [x] Usuarios demo con roles y credenciales solicitadas.
- [x] Indices Mongo `2dsphere`, compuesto y TTL 14400 s.
- [x] README con Modelo 4+1, escalabilidad y despliegue.
- [ ] **Pendiente del operador:** completar `MONGO_ATLAS_URI` real y rotar
      secretos para produccion.
