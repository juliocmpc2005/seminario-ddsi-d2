"""Pruebas automáticas de la lógica de pedidos.

Usan SQLite (viene incluido en Python) solo como banco de pruebas rápido: sus
transacciones y savepoints se comportan igual para lo que aquí se comprueba y
no hacen falta red ni contraseña. La aplicación entregada usa siempre Oracle;
la validación real contra Oracle está en tests/oracle_integration.py.

Ejecutar: .venv/bin/python -m unittest discover -s tests -v
"""
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from seminario.db import ROOT, connection_string, show_tables
from seminario.orders import Orders, STOCK_INITIAL
from seminario.__main__ import integer, main_menu, new_order

# SQLite no tiene tipo DATE: las fechas se guardan como texto AAAA-MM-DD.
sqlite3.register_adapter(date, lambda value: value.isoformat())


class TransactionsTest(unittest.TestCase):
    def setUp(self):
        """Antes de cada prueba: una BD nueva con las tablas y el stock inicial."""
        self.directory = tempfile.TemporaryDirectory()
        path = Path(self.directory.name) / "test.db"
        # Dos conexiones al mismo fichero = dos sesiones: la aplicación (db) y
        # un observador que, como SQL Developer, solo ve lo confirmado.
        self.db = sqlite3.connect(path)
        self.observer = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys = ON")  # SQLite no las comprueba por defecto.
        self.db.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
        self.db.executemany("INSERT INTO STOCK VALUES (?, ?)", STOCK_INITIAL)
        self.db.commit()
        self.service = Orders(self.db)

    def tearDown(self):
        """Después de cada prueba: cerrar todo y borrar la BD temporal."""
        self.db.rollback()
        self.db.close()
        self.observer.close()
        self.directory.cleanup()

    # --- Funciones de ayuda -------------------------------------------------
    def stock(self, db=None):
        """Stock del producto 1 visto por la conexión indicada (por defecto, la aplicación)."""
        return (db or self.db).execute("SELECT CANTIDAD FROM STOCK WHERE CPRODUCTO = 1").fetchone()[0]

    def count(self, table, db=None):
        """Número de filas de una tabla."""
        return (db or self.db).execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def begin(self, code=1):
        self.service.begin(code, 10, date(2026, 11, 3))

    # --- COMMIT -------------------------------------------------------------
    def test_commit_and_independent_observer(self):
        """Hasta el COMMIT, la otra sesión no ve ni el pedido ni el stock descontado."""
        self.begin()
        self.service.add(1, 7)
        self.assertEqual(self.stock(), 93)                  # nuestra sesión sí lo ve
        self.assertEqual(self.stock(self.observer), 100)    # la otra todavía no
        self.assertEqual(self.count("PEDIDO", self.observer), 0)
        self.service.finish()                               # COMMIT
        self.assertEqual(self.stock(self.observer), 93)
        self.assertEqual(self.count("PEDIDO", self.observer), 1)

    # --- ROLLBACK TO SAVEPOINT (opción 2 del submenú) -------------------------
    def test_clear_preserves_header_and_restores_all_stock(self):
        """Eliminar detalles: se van los detalles, vuelve el stock, queda la cabecera."""
        self.begin()
        self.service.add(1, 20)
        self.service.add(2, 10)
        self.service.clear()
        self.service.clear()  # El savepoint sigue existiendo: se puede repetir.
        self.assertEqual(self.count("PEDIDO"), 1)
        self.assertEqual(self.count("DETALLE_PEDIDO"), 0)
        self.assertEqual(self.db.execute("SELECT * FROM STOCK ORDER BY CPRODUCTO").fetchall(),
                         list(STOCK_INITIAL))
        # La transacción sigue activa: se puede seguir añadiendo y confirmar.
        self.service.add(1, 4)
        self.service.finish()
        self.assertEqual(self.stock(self.observer), 96)

    # --- ROLLBACK (opción 3 del submenú) --------------------------------------
    def test_cancel_restores_header_details_and_stock(self):
        """Cancelar: no queda ni cabecera ni detalles y el stock vuelve a su valor."""
        self.begin()
        self.service.add(1, 100)
        self.service.cancel()
        self.assertEqual(self.stock(self.observer), 100)
        self.assertEqual(self.count("PEDIDO"), 0)
        self.assertEqual(self.count("DETALLE_PEDIDO"), 0)

    # --- Añadir detalles (opción 1 del submenú) -------------------------------
    def test_missing_product_and_insufficient_stock_keep_previous_lines(self):
        """Una línea rechazada (sin stock o producto inexistente) no afecta a las anteriores."""
        self.begin()
        self.service.add(1, 10)
        for product, quantity in ((1, 91), (999, 1)):  # quedan 90; el 999 no existe
            with self.assertRaises(ValueError):
                self.service.add(product, quantity)
        self.assertEqual(self.stock(), 90)
        self.assertEqual(self.db.execute("SELECT CANTIDAD FROM DETALLE_PEDIDO").fetchone()[0], 10)

    def test_same_product_accumulates_and_stock_can_reach_zero(self):
        """El mismo producto dos veces da una sola línea con la suma; el stock puede llegar a 0."""
        self.begin()
        self.service.add(1, 30)
        self.service.add(1, 70)
        self.assertEqual(self.stock(), 0)
        self.assertEqual(self.db.execute("SELECT CANTIDAD FROM DETALLE_PEDIDO").fetchall(), [(100,)])

    def test_insert_error_rolls_back_just_current_line_and_stock(self):
        """Si falla el INSERT del detalle tras descontar el stock, el savepoint de
        la línea devuelve ese stock y el resto del pedido sigue intacto."""
        # Disparador que hace fallar a propósito el INSERT del producto 2.
        self.db.execute("CREATE TRIGGER fail_line BEFORE INSERT ON DETALLE_PEDIDO "
                        "WHEN NEW.CPRODUCTO = 2 BEGIN SELECT RAISE(ABORT, 'fallo simulado'); END")
        self.db.commit()
        self.begin()
        self.service.add(1, 5)
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.add(2, 7)
        self.assertEqual(self.db.execute("SELECT CANTIDAD FROM STOCK WHERE CPRODUCTO=2").fetchone()[0], 80)
        self.assertEqual(self.stock(), 95)
        self.service.finish()
        self.assertEqual(self.stock(self.observer), 95)

    def test_duplicate_order_does_not_modify_committed_data(self):
        """Un código de pedido repetido se rechaza y el pedido confirmado no cambia."""
        self.begin()
        self.service.finish()
        with self.assertRaises(sqlite3.IntegrityError):
            self.begin()
        self.assertEqual(self.count("PEDIDO"), 1)

    # --- Menús ----------------------------------------------------------------
    def test_integer_repeats_until_valid(self):
        """La entrada de números rechaza todo lo que no sea un entero entre 1 y 999999999."""
        answers = ["0", "-1", "1.2", "abc", "", "1000000000", "7"]
        with patch("builtins.input", side_effect=answers), redirect_stdout(StringIO()):
            self.assertEqual(integer("Número: "), 7)

    def test_menu_add_clear_cancel_always_displays_tables(self):
        """El enunciado exige mostrar la BD después de las opciones 1, 2 y 3 del submenú."""
        # Respuestas del usuario: pedido 123, cliente 45, fecha; después
        # 1 = añadir (producto 1, cantidad 7), 2 = eliminar detalles, 3 = cancelar.
        answers = ["123", "45", "2026-11-03", "1", "1", "7", "2", "3"]
        output = StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            new_order(self.service, self.db)
        self.assertEqual(output.getvalue().count("DETALLE_PEDIDO"), 3)  # se mostró 3 veces
        self.assertEqual(self.stock(), 100)

    def test_duplicate_order_in_menu_returns_to_main_menu(self):
        """Un error dentro del alta (código repetido) cancela y vuelve al menú principal."""
        self.begin(123)
        self.service.finish()
        # 2 = alta con el código 123 ya usado -> error; 4 = salir.
        answers = ["2", "123", "45", "", "4"]
        output = StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            main_menu(self.db)
        self.assertIn("Operación interrumpida", output.getvalue())
        self.assertEqual(self.count("PEDIDO", self.observer), 1)

    def test_eof_leaves_work_uncommitted_for_outer_cleanup(self):
        """Si el programa se interrumpe a mitad de un pedido, no se confirma nada."""
        answers = ["2", "123", "45", "2026-11-03", "1", "1", "7", EOFError()]
        with patch("builtins.input", side_effect=answers), redirect_stdout(StringIO()):
            with self.assertRaises(EOFError):
                main_menu(self.db)
        self.db.rollback()  # El mismo ROLLBACK final que hace main().
        self.assertEqual(self.stock(self.observer), 100)
        self.assertEqual(self.count("PEDIDO"), 0)

    # --- Conexión y presentación ------------------------------------------------
    def test_oracle_connection_format(self):
        """Formato de la cadena de conexión ODBC y rechazo del punto y coma."""
        value = connection_string("OracleSeminario", "//oracle0.ugr.es:1521/practbd", "x1234567", "a}b")
        self.assertEqual(value, "DRIVER={OracleSeminario};DBQ=//oracle0.ugr.es:1521/practbd;UID=x1234567;PWD=a}b")
        with self.assertRaises(ValueError):
            connection_string("OracleSeminario", "host", "user", "bad;PWD=other")

    def test_show_tables(self):
        """Mostrar tablas imprime las 10 filas de Stock."""
        output = StringIO()
        with redirect_stdout(output):
            show_tables(self.db)
        self.assertIn("(10 filas)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
