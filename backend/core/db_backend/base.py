"""
Backend MySQL/MariaDB de CONATACOCH.

Django 5.2 exige MariaDB >= 10.5, pero el entorno local (XAMPP/MariaDB 10.4)
es compatible con todo el SQL que usa el proyecto salvo `INSERT ... RETURNING`,
introducido en MariaDB 10.5. Este backend hereda el oficial y:

  * relaja la comprobacion de version minima (solo MariaDB 10.4);
  * desactiva `can_return_columns_from_insert`, de modo que Django obtenga el
    `lastrowid` clasico en lugar de `RETURNING`.

No altera el SQL de negocio ni las transacciones. Con MySQL 8.0 o MariaDB >=
10.5 se puede volver a `django.db.backends.mysql` sin cambios.
"""
from __future__ import annotations

from functools import cached_property

from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures as MySQLFeatures


class DatabaseFeatures(MySQLFeatures):
    @cached_property
    def can_return_columns_from_insert(self):
        """MariaDB 10.5+ soporta RETURNING; 10.4 no."""
        if (
            self.connection.mysql_is_mariadb
            and self.connection.mysql_version < (10, 5)
        ):
            return False
        return super().can_return_columns_from_insert


class DatabaseWrapper(MySQLDatabaseWrapper):
    features_class = DatabaseFeatures

    def check_database_version_supported(self) -> None:
        """Permite MariaDB 10.4 (fin de vida) en el entorno academico local."""
        if self.mysql_is_mariadb and self.mysql_version < (10, 4):
            from django.core.exceptions import ImproperlyConfigured

            raise ImproperlyConfigured(
                "CONATACOCH requiere MariaDB >= 10.4 o MySQL >= 8.0.11 "
                f"(detectado {self.mysql_version})."
            )
        return
