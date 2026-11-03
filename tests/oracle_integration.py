"""Validación real ODBC/Oracle en tablas temporales propias, nunca las de la aplicación.

Ejecución explícita: ./ejecutar.sh --probar-oracle
"""
from datetime import date
import getpass
import json
from uuid import uuid4

from seminario.db import ROOT, connect, query
from seminario.orders import Orders


def run(password=None):
    prefix = "T1" + uuid4().hex[:6].upper() + "_"
    if password is None:
        password = getpass.getpass("Contraseña Oracle para la validación (oculta): ")
    writer = reader = None
    created = False
    messages = []

    def passed(message):
        messages.append(message)
        print("OK:", message, flush=True)

    def scalar(connection, statement):
        return query(connection, statement)[1][0][0]

    try:
        writer = connect(password)
        reader = connect(password)
        password = ""
        service = Orders(writer, prefix)
        # Una colisión se aborta antes de llamar a reset(); no borrar tablas ajenas.
        count = scalar(writer, "SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME IN "
                       f"('{prefix}STOCK', '{prefix}PEDIDO', '{prefix}DETALLE_PEDIDO')")
        if count:
            raise RuntimeError("Colisión de nombres de prueba. Ejecuta de nuevo.")
        created = True
        service.reset()
        assert scalar(reader, f"SELECT COUNT(*) FROM {prefix}STOCK") == 10
        passed("DDL Oracle y 10 productos iniciales")

        service.begin(1, 1, date.today())
        service.add(1, 7)
        assert scalar(writer, f"SELECT CANTIDAD FROM {prefix}STOCK WHERE CPRODUCTO=1") == 93
        assert scalar(reader, f"SELECT CANTIDAD FROM {prefix}STOCK WHERE CPRODUCTO=1") == 100
        assert scalar(reader, f"SELECT COUNT(*) FROM {prefix}PEDIDO") == 0
        passed("otra sesión no ve cambios sin COMMIT")
        service.clear()
        service.clear()
        assert scalar(writer, f"SELECT COUNT(*) FROM {prefix}PEDIDO") == 1
        assert scalar(writer, f"SELECT COUNT(*) FROM {prefix}DETALLE_PEDIDO") == 0
        assert scalar(writer, f"SELECT CANTIDAD FROM {prefix}STOCK WHERE CPRODUCTO=1") == 100
        passed("ROLLBACK TO conserva cabecera y repone stock; se puede repetir")
        service.add(1, 8)
        service.add(1, 2)
        for product, quantity in ((1, 91), (999, 1)):
            try:
                service.add(product, quantity)
            except ValueError:
                pass
            else:
                raise AssertionError("Debió rechazar la línea")
        service.finish()
        assert scalar(reader, f"SELECT CANTIDAD FROM {prefix}STOCK WHERE CPRODUCTO=1") == 90
        assert scalar(reader, f"SELECT CANTIDAD FROM {prefix}DETALLE_PEDIDO WHERE CPEDIDO=1") == 10
        passed("COMMIT visible, producto repetido acumulado y stock insuficiente rechazado")
        service.begin(2, 1, date.today())
        service.add(1, 4)
        service.cancel()
        assert scalar(reader, f"SELECT COUNT(*) FROM {prefix}PEDIDO WHERE CPEDIDO=2") == 0
        assert scalar(reader, f"SELECT CANTIDAD FROM {prefix}STOCK WHERE CPRODUCTO=1") == 90
        passed("ROLLBACK completo elimina pedido y detalles y restaura stock")

        # Fuerza un fallo SQL real después de descontar stock, en las tablas de prueba.
        service.execute(f"ALTER TABLE {prefix}DETALLE_PEDIDO ADD CONSTRAINT "
                        f"{prefix}REJECT CHECK (CPRODUCTO <> 2)")
        service.begin(3, 1, date.today())
        service.add(1, 1)
        try:
            service.add(2, 3)
        except Exception as error:
            if "ORA-02290" not in str(error):
                raise
        else:
            raise AssertionError("La restricción de prueba debía rechazar la línea")
        assert scalar(writer, f"SELECT CANTIDAD FROM {prefix}STOCK WHERE CPRODUCTO=2") == 80
        assert scalar(writer, f"SELECT CANTIDAD FROM {prefix}STOCK WHERE CPRODUCTO=1") == 89
        service.cancel()
        passed("un fallo SQL al insertar revierte solo la línea y su descuento de stock")
        try:
            service.begin(1, 1, date.today())
        except Exception as error:
            if "ORA-00001" not in str(error):
                raise
        else:
            raise AssertionError("Pedido duplicado aceptado")
        passed("pedido duplicado rechazado sin dañar datos confirmados")
    finally:
        password = ""
        if reader is not None:
            try:
                reader.rollback()
            finally:
                reader.close()
        if writer is not None:
            try:
                writer.rollback()
                if created:
                    cleaner = Orders(writer, prefix)
                    for table in ("DETALLE_PEDIDO", "PEDIDO", "STOCK"):
                        try:
                            cleaner.execute(f"DROP TABLE {prefix}{table}")
                        except Exception as error:
                            if "ORA-00942" not in str(error):
                                raise
            finally:
                writer.close()
    (ROOT / ".local").mkdir(exist_ok=True)
    (ROOT / ".local/oracle-validation.json").write_text(
        json.dumps({"ok": True, "checks": messages}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Validación Oracle terminada. Tablas de prueba eliminadas; conexiones cerradas.")


if __name__ == "__main__":
    run()
