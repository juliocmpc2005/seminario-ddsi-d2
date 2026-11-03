"""Pruebas de lógica con transacciones reales SQLite; no sustituyen Oracle/ODBC."""
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from seminario.db import connection_string, show_tables
from seminario.orders import Orders, STOCK_INITIAL
from seminario.__main__ import main_menu, new_order

sqlite3.register_adapter(date, lambda value: value.isoformat())


class TransactionsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        path = Path(self.directory.name) / "test.db"
        self.db = sqlite3.connect(path)
        self.observer = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys = ON")
        schema = (Path(__file__).resolve().parent.parent / "sql/schema.sql").read_text()
        self.db.executescript(schema.replace("{prefix}", ""))
        self.db.executemany("INSERT INTO STOCK VALUES (?, ?)", STOCK_INITIAL)
        self.db.commit()
        self.service = Orders(self.db)

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        self.observer.close()
        self.directory.cleanup()

    def stock(self, db=None):
        return (db or self.db).execute("SELECT CANTIDAD FROM STOCK WHERE CPRODUCTO = 1").fetchone()[0]

    def begin(self, code=1):
        self.service.begin(code, 10, date(2026, 11, 3))

    def test_commit_and_independent_observer(self):
        self.begin()
        self.service.add(1, 7)
        self.assertEqual(self.stock(), 93)
        self.assertEqual(self.stock(self.observer), 100)
        self.assertEqual(self.observer.execute("SELECT COUNT(*) FROM PEDIDO").fetchone()[0], 0)
        self.service.finish()
        self.assertEqual(self.stock(self.observer), 93)
        self.assertEqual(self.observer.execute("SELECT COUNT(*) FROM PEDIDO").fetchone()[0], 1)

    def test_clear_preserves_header_and_restores_all_stock(self):
        self.begin()
        self.service.add(1, 20)
        self.service.add(2, 10)
        self.service.clear()
        self.service.clear()  # El punto de guardado sigue siendo utilizable.
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM PEDIDO").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM DETALLE_PEDIDO").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT * FROM STOCK ORDER BY CPRODUCTO").fetchall(), list(STOCK_INITIAL))
        self.service.add(1, 4)
        self.service.finish()
        self.assertEqual(self.stock(self.observer), 96)

    def test_cancel_restores_header_details_and_stock(self):
        self.begin()
        self.service.add(1, 100)
        self.service.cancel()
        self.assertEqual(self.stock(self.observer), 100)
        for table in ("PEDIDO", "DETALLE_PEDIDO"):
            self.assertEqual(self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)

    def test_missing_product_and_insufficient_stock_keep_previous_lines(self):
        self.begin()
        self.service.add(1, 10)
        for product, quantity in ((1, 91), (999, 1)):
            with self.assertRaises(ValueError):
                self.service.add(product, quantity)
        self.assertEqual(self.stock(), 90)
        self.assertEqual(self.db.execute("SELECT CANTIDAD FROM DETALLE_PEDIDO").fetchone()[0], 10)

    def test_same_product_accumulates_and_stock_can_reach_zero(self):
        self.begin()
        self.service.add(1, 30)
        self.service.add(1, 70)
        self.assertEqual(self.stock(), 0)
        self.assertEqual(self.db.execute("SELECT CANTIDAD FROM DETALLE_PEDIDO").fetchall(), [(100,)])

    def test_insert_error_rolls_back_just_current_line_and_stock(self):
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
        self.begin()
        self.service.finish()
        with self.assertRaises(sqlite3.IntegrityError):
            self.begin()
        self.assertIsNone(self.service.current)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM PEDIDO").fetchone()[0], 1)

    def test_input_validation_and_invalid_service_state(self):
        for quantity in (0, -1, 1.2, True, 1_000_000_000):
            with self.assertRaises(ValueError):
                self.service.begin(quantity, 1, date.today())
        with self.assertRaises(ValueError):
            self.service.add(1, 1)
        self.begin()
        with self.assertRaises(ValueError):
            self.service.reset()
        with self.assertRaises(ValueError):
            self.begin(2)

    def test_menu_add_clear_cancel_always_displays_tables(self):
        answers = ["123", "45", "2026-11-03", "1", "1", "7", "2", "3"]
        output = StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output):
            new_order(self.service, self.db)
        self.assertEqual(output.getvalue().count("DETALLE_PEDIDO"), 3)
        self.assertEqual(self.stock(), 100)

    def test_eof_leaves_work_uncommitted_for_outer_cleanup(self):
        answers = ["2", "123", "45", "2026-11-03", "1", "1", "7", EOFError()]
        with patch("builtins.input", side_effect=answers), redirect_stdout(StringIO()):
            with self.assertRaises(EOFError):
                main_menu(self.db)
        self.db.rollback()  # Mismo cierre explícito que en main().
        self.assertEqual(self.stock(self.observer), 100)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM PEDIDO").fetchone()[0], 0)

    def test_oracle_connection_format(self):
        value = connection_string("OracleSeminario", "//oracle0.ugr.es:1521/practbd", "x1234567", "a}b")
        self.assertEqual(value, "DRIVER={OracleSeminario};DBQ=//oracle0.ugr.es:1521/practbd;UID=x1234567;PWD=a}b")
        with self.assertRaises(ValueError):
            connection_string("OracleSeminario", "host", "user", "bad;PWD=other")

    def test_show_tables(self):
        output = StringIO()
        with redirect_stdout(output):
            show_tables(self.db)
        self.assertIn("(10 filas)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
