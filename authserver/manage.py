#!/usr/bin/env python3
import os
import sys

import pymysql

pymysql.install_as_MySQLdb()


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "authserver.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
