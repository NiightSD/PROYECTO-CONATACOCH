"""
CONATACOCH project package.

Se usa PyMySQL como driver MySQL puro Python (sin dependencias nativas en la
imagen slim). El shim expone la API compatible con MySQLdb que Django espera.
En entornos donde solo se usa SQLite (pruebas), el import se omite.
"""
try:  # pragma: no cover - depende del driver instalado
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:  # pragma: no cover
    pass
