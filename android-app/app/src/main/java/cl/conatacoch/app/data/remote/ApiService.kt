package cl.conatacoch.app.data.remote

import cl.conatacoch.app.data.remote.dto.ConductorPerfilDto
import cl.conatacoch.app.data.remote.dto.CuposRequestDto
import cl.conatacoch.app.data.remote.dto.CuposResponseDto
import cl.conatacoch.app.data.remote.dto.EtaRequestDto
import cl.conatacoch.app.data.remote.dto.EtaResponseDto
import cl.conatacoch.app.data.remote.dto.FleetResponseDto
import cl.conatacoch.app.data.remote.dto.LineaDto
import cl.conatacoch.app.data.remote.dto.LoginRequestDto
import cl.conatacoch.app.data.remote.dto.LoginResponseDto
import cl.conatacoch.app.data.remote.dto.PagoConfirmarRequestDto
import cl.conatacoch.app.data.remote.dto.PagoConfirmarResponseDto
import cl.conatacoch.app.data.remote.dto.PagoQrRequestDto
import cl.conatacoch.app.data.remote.dto.PagoQrResponseDto
import cl.conatacoch.app.data.remote.dto.PaginatedDto
import cl.conatacoch.app.data.remote.dto.ParaderoDto
import cl.conatacoch.app.data.remote.dto.RefreshRequestDto
import cl.conatacoch.app.data.remote.dto.RefreshResponseDto
import cl.conatacoch.app.data.remote.dto.TelemetriaRequestDto
import cl.conatacoch.app.data.remote.dto.TelemetriaResponseDto
import cl.conatacoch.app.data.remote.dto.TransaccionDto
import cl.conatacoch.app.data.remote.dto.TurnoRequestDto
import cl.conatacoch.app.data.remote.dto.TurnoResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Contrato Retrofit de la API CONATACOCH.
 *
 * Rutas relativas a BuildConfig.API_BASE_URL (por defecto
 * http://10.0.2.2:8000/api/ desde el emulador).
 */
interface ApiService {

    // ------------------------------------------------------------- Auth
    @POST("auth/login/")
    suspend fun login(@Body body: LoginRequestDto): LoginResponseDto

    @POST("auth/refresh/")
    suspend fun refresh(@Body body: RefreshRequestDto): RefreshResponseDto

    // -------------------------------------------------------- Catalogos
    @GET("lineas/")
    suspend fun lineas(
        @Query("search") search: String? = null,
        @Query("folio") folio: Int? = null,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
    ): PaginatedDto<LineaDto>

    @GET("paraderos/")
    suspend fun paraderos(
        @Query("linea") lineaId: Int,
        @Query("page_size") pageSize: Int = 100,
    ): PaginatedDto<ParaderoDto>

    // ------------------------------------------------------- Pasajero
    @POST("eta/calcular/")
    suspend fun calcularEta(@Body body: EtaRequestDto): EtaResponseDto

    @GET("telemetria/flota/")
    suspend fun flota(@Query("linea_id") lineaId: Int? = null): FleetResponseDto

    @POST("pagos/qr/")
    suspend fun crearPagoQr(@Body body: PagoQrRequestDto): PagoQrResponseDto

    @GET("transacciones/")
    suspend fun transacciones(
        @Query("estado") estado: String? = null,
        @Query("conductor") conductorId: Int? = null,
        @Query("search") search: String? = null,
        @Query("page_size") pageSize: Int = 20,
    ): PaginatedDto<TransaccionDto>

    // ------------------------------------------------------ Conductor
    @GET("conductor/perfil/")
    suspend fun perfilConductor(): ConductorPerfilDto

    @POST("conductor/iniciar-turno/")
    suspend fun iniciarTurno(@Body body: TurnoRequestDto): TurnoResponseDto

    @POST("conductor/finalizar-turno/")
    suspend fun finalizarTurno(@Body body: TurnoRequestDto): TurnoResponseDto

    @POST("conductor/cupos/")
    suspend fun actualizarCupos(@Body body: CuposRequestDto): CuposResponseDto

    @POST("telemetria/enviar/")
    suspend fun enviarTelemetria(@Body body: TelemetriaRequestDto): TelemetriaResponseDto

    @POST("pagos/confirmar/")
    suspend fun confirmarPago(@Body body: PagoConfirmarRequestDto): PagoConfirmarResponseDto
}
