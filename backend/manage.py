#!/usr/bin/env python
"""Utilidad de linea de comandos de Django para CONATACOCH."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conatacoch.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "No se pudo importar Django. Verifique que el entorno virtual este "
            "activo y que las dependencias esten instaladas."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
