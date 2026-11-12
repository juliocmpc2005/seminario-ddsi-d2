"""Validación real contra Oracle por ODBC, con dos sesiones.

Hace automáticamente lo mismo que la demostración de la defensa: una conexión
("writer") trabaja como la aplicación y otra ("reader") mira como lo haría
SQL Developer, para comprobar qué se ve antes y después de COMMIT/ROLLBACK.

AVISO: usa las tablas de la aplicación. Las borra y las vuelve a crear al
empezar y al terminar, igual que la opción 1 del menú.

Ejecutar: ./ejecutar.sh --probar-oracle   (o doble clic en Validar_Oracle.command)
"""
from datetime import date
import getpass

from seminario.db import connect, query
from seminario.orders import Orders


def value(connection, sql):
    """Devuelve el único valor (primera fila, primera columna) de una consulta."""
    return query(connection, sql)[1][0][0]


def expect(actual, expected, what):
    """Detiene la validación con un mensaje claro si un valor no es el esperado."""
    if actual != expected:
        raise RuntimeError(f"Validación fallida: {what}: esperado {expected}, obtenido {actual}")


def run():
    print("Esta validación BORRA y vuelve a crear STOCK, PEDIDO y DETALLE_PEDIDO.")
    if input("Escribe BORRAR para continuar: ") != "BORRAR":
        print("Validación cancelada; no se ha tocado nada.")
        return
    password = getpass.getpass("Contraseña Oracle (oculta): ")
    stock_1 = "SELECT CANTIDAD FROM STOCK WHERE CPRODUCTO = 1"
    writer = reader = None
    try:
        writer = connect(password)  # sesión que hace los cambios
        reader = connect(password)  # sesión independiente que solo consulta
        service = Orders(writer)

        service.reset()
        expect(value(reader, "SELECT COUNT(*) FROM STOCK"), 10, "productos iniciales")
        print("OK: tablas creadas con 10 productos")

        # Cambios sin confirmar: los ve quien los hace, no la otra sesión.
        service.begin(1, 1, date.today())
        service.add(1, 7)
        expect(value(writer, stock_1), 93, "stock visto por la aplicación")
        expect(value(reader, stock_1), 100, "stock visto por la otra sesión")
        expect(value(reader, "SELECT COUNT(*) FROM PEDIDO"), 0, "pedidos vistos por la otra sesión")
        print("OK: la otra sesión no ve los cambios sin COMMIT")

        # Eliminar detalles = ROLLBACK TO SAVEPOINT (dos veces: es repetible).
        service.clear()
        service.clear()
        expect(value(writer, "SELECT COUNT(*) FROM PEDIDO"), 1, "cabecera conservada")
        expect(value(writer, "SELECT COUNT(*) FROM DETALLE_PEDIDO"), 0, "detalles eliminados")
        expect(value(writer, stock_1), 100, "stock repuesto")
        print("OK: ROLLBACK TO conserva la cabecera, repone el stock y se puede repetir")

        # Producto repetido (8 + 2), stock insuficiente, producto inexistente y COMMIT.
        service.add(1, 8)
        service.add(1, 2)
        for product, quantity in ((1, 91), (999, 1)):
            try:
                service.add(product, quantity)
            except ValueError:
                pass  # Rechazo esperado.
            else:
                raise RuntimeError("Validación fallida: se aceptó una línea sin stock")
        service.finish()
        expect(value(reader, stock_1), 90, "stock confirmado")
        expect(value(reader, "SELECT CANTIDAD FROM DETALLE_PEDIDO WHERE CPEDIDO = 1"), 10,
               "cantidad acumulada")
        print("OK: COMMIT visible desde la otra sesión; cantidades acumuladas; sin stock se rechaza")

        # Cancelar = ROLLBACK completo.
        service.begin(2, 1, date.today())
        service.add(1, 4)
        service.cancel()
        expect(value(reader, "SELECT COUNT(*) FROM PEDIDO WHERE CPEDIDO = 2"), 0, "pedido cancelado")
        expect(value(reader, stock_1), 90, "stock tras cancelar")
        print("OK: ROLLBACK elimina el pedido y sus detalles y restaura el stock")

        # Fallo SQL real después de descontar el stock: una restricción temporal
        # impide insertar detalles del producto 2 (desaparece con el reset final).
        service.execute("ALTER TABLE DETALLE_PEDIDO ADD CONSTRAINT PRUEBA_RECHAZO CHECK (CPRODUCTO <> 2)")
        service.begin(3, 1, date.today())
        service.add(1, 1)
        try:
            service.add(2, 3)
        except Exception as error:
            if "ORA-02290" not in str(error):  # ORA-02290 = restricción CHECK violada
                raise
        else:
            raise RuntimeError("Validación fallida: la restricción de prueba no actuó")
        expect(value(writer, "SELECT CANTIDAD FROM STOCK WHERE CPRODUCTO = 2"), 80, "stock de la línea fallida")
        expect(value(writer, stock_1), 89, "stock de la línea anterior")
        service.cancel()
        print("OK: un fallo al insertar deshace solo esa línea y su descuento de stock")

        # Clave primaria: el pedido 1 ya está confirmado.
        try:
            service.begin(1, 1, date.today())
        except Exception as error:
            if "ORA-00001" not in str(error):  # ORA-00001 = clave duplicada
                raise
        else:
            raise RuntimeError("Validación fallida: se aceptó un pedido duplicado")
        service.cancel()
        print("OK: código de pedido duplicado rechazado")

        service.reset()  # Deja las tablas limpias, con el stock inicial.
        print("Validación Oracle completada. Tablas reiniciadas con el stock inicial.")
    finally:
        # Pase lo que pase: deshacer lo pendiente y cerrar las dos sesiones.
        for connection in (reader, writer):
            if connection is not None:
                try:
                    connection.rollback()
                finally:
                    connection.close()


if __name__ == "__main__":
    run()
