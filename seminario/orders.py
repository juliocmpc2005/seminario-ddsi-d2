"""Operaciones del pedido: una conexión y una transacción por pedido."""
from contextlib import closing
from datetime import date
from pathlib import Path
import re

STOCK_INITIAL = ((1, 100), (2, 80), (3, 60), (4, 40), (5, 20),
                 (6, 150), (7, 75), (8, 50), (9, 30), (10, 10))
MAX_NUMBER = 999_999_999


def positive_integer(value):
    if type(value) is not int or not 1 <= value <= MAX_NUMBER:
        raise ValueError(f"Debe ser un entero entre 1 y {MAX_NUMBER}.")
    return value


class Orders:
    def __init__(self, connection, prefix=""):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,9}_|", prefix):
            raise ValueError("Prefijo SQL inválido")
        self.connection = connection
        self.prefix = prefix
        self.current = None

    def execute(self, sql, params=()):
        with closing(self.connection.cursor()) as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    def reset(self):
        """DDL hace commits implícitos en Oracle; nunca ejecutarlo durante un pedido."""
        if self.current is not None:
            raise ValueError("Hay un pedido en curso.")
        self.connection.rollback()
        for table in ("DETALLE_PEDIDO", "PEDIDO", "STOCK"):
            try:
                self.execute(f"DROP TABLE {self.prefix}{table}")
            except Exception as error:
                if "ORA-00942" not in str(error):
                    raise
        schema = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text()
        for statement in schema.split(";"):
            if statement.strip():
                self.execute(statement.replace("{prefix}", self.prefix))
        try:
            for product, quantity in STOCK_INITIAL:
                self.execute(f"INSERT INTO {self.prefix}STOCK VALUES (?, ?)", (product, quantity))
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    def begin(self, order, client, day):
        if self.current is not None:
            raise ValueError("Ya hay un pedido en curso.")
        positive_integer(order)
        positive_integer(client)
        if type(day) is not date:
            raise ValueError("Fecha no válida.")
        try:
            self.execute(f"INSERT INTO {self.prefix}PEDIDO VALUES (?, ?, ?)", (order, client, day))
            self.execute("SAVEPOINT pedido_sin_detalles")
            self.current = order
        except BaseException:
            self.connection.rollback()
            raise

    def require_order(self):
        if self.current is None:
            raise ValueError("No hay ningún pedido en curso.")

    def add(self, product, quantity):
        self.require_order()
        positive_integer(product)
        positive_integer(quantity)
        self.execute("SAVEPOINT antes_detalle")
        try:
            # El UPDATE condicional evita vender stock que otra sesión acaba de consumir.
            affected = self.execute(
                f"UPDATE {self.prefix}STOCK SET CANTIDAD = CANTIDAD - ? "
                "WHERE CPRODUCTO = ? AND CANTIDAD >= ?", (quantity, product, quantity))
            if affected != 1:
                raise ValueError("Producto inexistente o stock insuficiente.")
            affected = self.execute(
                f"UPDATE {self.prefix}DETALLE_PEDIDO SET CANTIDAD = CANTIDAD + ? "
                "WHERE CPEDIDO = ? AND CPRODUCTO = ?", (quantity, self.current, product))
            if affected == 0:
                self.execute(f"INSERT INTO {self.prefix}DETALLE_PEDIDO VALUES (?, ?, ?)",
                             (self.current, product, quantity))
        except BaseException:
            # También repone stock si el INSERT falla después de descontarlo.
            self.execute("ROLLBACK TO antes_detalle")
            raise

    def clear(self):
        self.require_order()
        # Conserva la cabecera y deshace TODOS los detalles y descuentos de stock.
        self.execute("ROLLBACK TO pedido_sin_detalles")

    def cancel(self):
        self.connection.rollback()
        self.current = None

    def finish(self):
        self.require_order()
        self.connection.commit()
        self.current = None
