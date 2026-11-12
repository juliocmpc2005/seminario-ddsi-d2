"""Conexión a Oracle mediante ODBC y utilidades para consultar y mostrar tablas.

Cadena de componentes (la del diagrama del enunciado):

    aplicación Python -> pyodbc -> unixODBC (Driver Manager) -> driver ODBC de
    Oracle (Instant Client) -> listener de oracle0.ugr.es -> base de datos practbd

Este módulo no decide nada sobre transacciones: solo abre la conexión con el
autocommit desactivado. Los COMMIT, ROLLBACK y SAVEPOINT están en orders.py.
"""
import configparser
import getpass
from pathlib import Path

# Carpeta raíz del proyecto (la que contiene config.ini y sql/).
ROOT = Path(__file__).resolve().parent.parent


def connection_string(driver, server, user, password):
    """Construye la cadena de conexión ODBC: pares CLAVE=valor separados por ';'.

    - DRIVER: nombre con el que el driver de Oracle está registrado en el
      Driver Manager (fichero odbcinst.ini). Va entre llaves.
    - DBQ: a qué base de datos conectar, con formato //servidor:puerto/servicio.
    - UID y PWD: usuario y contraseña de Oracle.
    """
    # Como ';' separa los campos, un valor que lo contenga rompería la cadena.
    for value in (server, user, password):
        if ";" in value:
            raise ValueError("Los datos de conexión no pueden contener punto y coma.")
    return f"DRIVER={{{driver}}};DBQ={server};UID={user};PWD={password}"


def connect(password=None):
    """Abre y devuelve una conexión (una sesión de Oracle) con autocommit desactivado."""
    # Se importa aquí, y no arriba, para que las pruebas con SQLite funcionen
    # incluso en un equipo que no tenga instalado el Driver Manager ODBC.
    import pyodbc

    # config.ini guarda servidor, puerto, servicio, usuario y nombre del driver.
    # La contraseña nunca se guarda: se pide por teclado sin mostrarla.
    config = configparser.ConfigParser()
    config.read(ROOT / "config.ini", encoding="utf-8")
    oracle = config["oracle"]
    user = oracle.get("usuario", "").strip() or input("Usuario Oracle: ").strip()
    if password is None:
        password = getpass.getpass("Contraseña Oracle (oculta): ")
    server = f"//{oracle['host']}:{oracle['puerto']}/{oracle['servicio']}"

    # autocommit=False es la clave del seminario: por defecto ODBC confirmaría
    # (COMMIT) cada sentencia por separado. Al desactivarlo, la transacción queda
    # abierta hasta que NOSOTROS llamemos a commit() o rollback().
    # timeout=10: segundos máximos de espera al iniciar sesión.
    return pyodbc.connect(connection_string(oracle["driver"], server, user, password),
                          autocommit=False, timeout=10)


def query(connection, sql, params=()):
    """Ejecuta un SELECT y devuelve (nombres de columnas, lista de filas)."""
    cursor = connection.cursor()
    cursor.execute(sql, params)
    # cursor.description trae una tupla por columna; su primer elemento es el nombre.
    headers = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    return headers, rows


def print_table(headers, rows):
    """Imprime una tabla alineada en la consola."""
    # Todo a texto para poder medir anchuras (None es el NULL de SQL).
    data = [["NULL" if value is None else str(value) for value in row] for row in rows]
    # Cada columna es tan ancha como su texto más largo (cabecera incluida).
    widths = [max(len(text) for text in column) for column in zip(headers, *data)]
    print(" | ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in data:
        print(" | ".join(value.ljust(width) for value, width in zip(row, widths)))
    print(f"({len(rows)} filas)")


def show_tables(connection):
    """Muestra el contenido de las tres tablas, tal y como lo ve ESTA sesión.

    Dentro de un pedido se ven también los cambios aún sin confirmar; otra
    sesión (SQL Developer, Consultar.command) solo ve lo confirmado con COMMIT.
    """
    for table, order in (("STOCK", "CPRODUCTO"), ("PEDIDO", "CPEDIDO"),
                         ("DETALLE_PEDIDO", "CPEDIDO, CPRODUCTO")):
        print(f"\n{table}")
        print_table(*query(connection, f"SELECT * FROM {table} ORDER BY {order}"))
