"""Configuración ODBC. La contraseña solo vive en memoria."""
import configparser
import getpass
import os
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def configuration():
    config = configparser.ConfigParser(interpolation=None)
    config.read(ROOT / "config.ini", encoding="utf-8")
    return config["oracle"]


def oracle_value(value):
    # Oracle ODBC en macOS interpreta literalmente las llaves en DBQ/UID/PWD.
    # No permitir separadores que puedan introducir otro atributo ODBC.
    value = str(value)
    if any(character in value for character in ";\r\n\x00"):
        raise ValueError("Este controlador Oracle ODBC no admite punto y coma ni saltos de línea "
                         "en los datos de conexión.")
    return value


def connection_string(driver, server, user, password):
    quoted_driver = "{" + str(driver).replace("}", "}}") + "}"
    return f"DRIVER={quoted_driver};" + ";".join(
        f"{key}={oracle_value(value)}" for key, value in
        (("DBQ", server), ("UID", user), ("PWD", password)))


def connect(password=None):
    import pyodbc
    config = configuration()
    user = config.get("usuario", "").strip() or input("Usuario Oracle: ").strip()
    if password is None:
        password = getpass.getpass("Contraseña Oracle (oculta): ")
    driver = os.environ.get("ORACLE_ODBC_DRIVER", config.get("driver", "OracleSeminario"))
    server = f"//{config['host']}:{config['puerto']}/{config['servicio']}"
    attributes = connection_string(driver, server, user, password)
    try:
        connection = pyodbc.connect(attributes, autocommit=False, timeout=10)
    finally:
        password = ""
        attributes = ""
    # Oracle ODBC en macOS no implementa el atributo que usa connection.timeout.
    # El timeout de login se establece en connect(); no configurar el otro aquí.
    return connection


def query(connection, sql, params=()):
    with closing(connection.cursor()) as cursor:
        cursor.execute(sql, params)
        return [column[0] for column in cursor.description], cursor.fetchall()


def print_table(headers, rows):
    data = [[str(value) if value is not None else "NULL" for value in row] for row in rows]
    widths = [max(len(str(h)), *(len(row[i]) for row in data)) if data else len(str(h))
              for i, h in enumerate(headers)]
    print(" | ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
    print("-+-".join("-" * w for w in widths))
    for row in data:
        print(" | ".join(value.ljust(w) for value, w in zip(row, widths)))
    print(f"({len(rows)} filas)")


def show_tables(connection, prefix=""):
    for table, order in (("STOCK", "CPRODUCTO"), ("PEDIDO", "CPEDIDO"),
                         ("DETALLE_PEDIDO", "CPEDIDO, CPRODUCTO")):
        print(f"\n{table}")
        print_table(*query(connection, f"SELECT * FROM {prefix}{table} ORDER BY {order}"))
