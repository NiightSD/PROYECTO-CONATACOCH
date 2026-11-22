package cl.conatacoch.app.core

import cl.conatacoch.app.BuildConfig
import cl.conatacoch.app.data.remote.ApiService
import com.google.gson.GsonBuilder
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/** Construccion de Retrofit/OkHttp con interceptor JWT y refresh automatico. */
object NetworkModule {

    fun createApi(sessionManager: SessionManager): ApiService {
        val gson = GsonBuilder().setLenient().create()

        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BASIC
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }

        val baseClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(25, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()

        // Cliente sin authenticator: se usa solo para renovar el token.
        val plainRetrofit = Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(baseClient)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()

        val refreshApi = plainRetrofit.create(ApiService::class.java)

        val authClient = baseClient.newBuilder()
            .addInterceptor(AuthInterceptor(sessionManager))
            .authenticator(TokenAuthenticator(sessionManager, refreshApi))
            .build()

        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(authClient)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
            .create(ApiService::class.java)
    }
}
