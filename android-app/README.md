# android-app (reservado)

La aplicacion Android para conductores y pasajeros pertenece a la **Fase 2**.

En esta fase solo se reserva la carpeta dentro del monorepo. La app consumira:

- `POST /api/token/` para autenticacion JWT.
- `GET /api/lineas/` y `GET /api/paraderos/` para el mapa.
- `GET /api/conductores/?en_turno=true` para disponibilidad.
- Futuro `POST /api/telemetria/` (Fase 2) para enviar ubicacion GPS al
  cluster MongoDB Atlas (`telemetria_ubicacion`).

Stack previsto: Kotlin + Jetpack Compose + Retrofit + Maps SDK.
