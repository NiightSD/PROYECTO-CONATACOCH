# Perfil de pasajero (tabla cliente) - Fase 3
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_add_otp_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "telefono",
                    models.CharField(
                        blank=True, default="", max_length=20, verbose_name="telefono"
                    ),
                ),
                (
                    "direccion",
                    models.CharField(
                        blank=True, default="", max_length=200, verbose_name="direccion"
                    ),
                ),
                (
                    "comuna",
                    models.CharField(
                        blank=True, default="", max_length=100, verbose_name="comuna"
                    ),
                ),
                (
                    "fecha_registro",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="fecha de registro",
                    ),
                ),
                (
                    "usuario",
                    models.OneToOneField(
                        limit_choices_to={"rol": "CLIENTE"},
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cliente",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="usuario cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "cliente",
                "verbose_name_plural": "clientes",
                "db_table": "cliente",
                "ordering": ["usuario__nombre"],
                "indexes": [
                    models.Index(fields=["comuna"], name="idx_cliente_comuna")
                ],
            },
        ),
    ]
