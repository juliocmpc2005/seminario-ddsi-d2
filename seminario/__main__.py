"""Interfaz de consola: menú principal y submenú de alta de pedido.

Se arranca con ./ejecutar.sh (equivale a "python -m seminario"). Opciones:

    (sin opciones)    aplicación con el menú del enunciado
    --consulta        cliente de solo lectura, para mirar desde OTRA sesión
    --comprobar       prueba la conexión y termina
    --probar-oracle   validación automática de las transacciones en Oracle
"""
import argparse
from datetime import date
import sys

from .db import connect, print_table, query, show_tables
from .orders import Orders

# Las columnas numéricas son NUMBER(9): el mayor valor admitido tiene 9 cifras.
MAX_NUMBER = 999_999_999


def integer(prompt):
    """Pide un entero positivo y repite la pregunta hasta que sea válido."""
    while True:
        text = input(prompt).strip()
        if text.isdecimal() and 1 <= int(text) <= MAX_NUMBER:
            return int(text)
        print(f"Debe ser un entero entre 1 y {MAX_NUMBER}.")


def order_date():
    """Pide la fecha del pedido; con Intro se usa la de hoy."""
    while True:
        text = input("Fecha (AAAA-MM-DD, Intro = hoy): ").strip()
        try:
            return date.fromisoformat(text) if text else date.today()
        except ValueError:
            print("Introduce una fecha válida en formato AAAA-MM-DD.")


def error_message(error):
    """Traduce los errores de Oracle más habituales a un mensaje entendible."""
    message = str(error)
    if "ORA-00942" in message:  # La tabla o vista no existe.
        return "Faltan tablas. Usa la opción 1 del menú principal para crearlas."
    if "ORA-00001" in message:  # Clave primaria repetida.
        return "Ya existe ese código de pedido. Utiliza otro."
    if "ORA-01017" in message:  # Usuario o contraseña no válidos.
        return "Usuario o contraseña Oracle incorrectos."
    if any(code in message for code in ("ORA-12170", "ORA-12541", "ORA-12154", "HYT00")):
        return "No se puede conectar. Revisa VPN/Eduroam, servidor, puerto y servicio."
    return message


def new_order(service, db):
    """Opción 2 del menú principal: alta de un pedido (una transacción)."""
    # Datos básicos del pedido e INSERT en PEDIDO: aquí comienza la transacción.
    service.begin(integer("Código de pedido: "), integer("Código de cliente: "), order_date())
    while True:
        print("\n1. Añadir detalle de producto\n2. Eliminar todos los detalles de producto"
              "\n3. Cancelar pedido\n4. Finalizar pedido")
        option = input("Opción: ").strip()
        if option == "1":
            product, quantity = integer("Código de producto: "), integer("Cantidad: ")
            try:
                service.add(product, quantity)
                print("Detalle añadido. Cambios pendientes de confirmar.")
            except Exception as error:
                # add() ya ha deshecho solo esa línea; el resto del pedido sigue.
                print("No se añadió el detalle:", error_message(error))
            show_tables(db)  # El enunciado pide mostrar la BD tras las opciones 1, 2 y 3.
        elif option == "2":
            service.clear()
            print("Detalles eliminados y stock repuesto; se conserva la cabecera.")
            show_tables(db)
        elif option == "3":
            service.cancel()
            print("Pedido cancelado (ROLLBACK).")
            show_tables(db)
            return  # Vuelve al menú principal.
        elif option == "4":
            service.finish()
            print("Pedido confirmado (COMMIT).")
            return  # Vuelve al menú principal.
        else:
            print("Opción no válida.")


def main_menu(db):
    """Menú principal del enunciado."""
    service = Orders(db)
    while True:
        print("\n1. Borrar y crear tablas e insertar stock inicial\n2. Dar de alta nuevo pedido"
              "\n3. Mostrar contenido de las tablas\n4. Salir")
        option = input("Opción: ").strip()
        try:
            if option == "1":
                # Confirmación extra porque el DDL no se puede deshacer.
                if input("Se borrarán STOCK, PEDIDO y DETALLE_PEDIDO. Escribe BORRAR: ") == "BORRAR":
                    service.reset()
                    print("Tablas creadas e insertadas las 10 tuplas de Stock.")
                    show_tables(db)
            elif option == "2":
                new_order(service, db)
            elif option == "3":
                show_tables(db)
            elif option == "4":
                return  # main() se encarga de cerrar la conexión.
            else:
                print("Opción no válida.")
        except EOFError:
            raise  # Ctrl+D (fin de la entrada): salir. Lo recoge main(), igual que Ctrl+C.
        except Exception as error:
            # Cualquier otro fallo (por ejemplo, un código de pedido que ya
            # existe) cancela lo que estuviera a medias y vuelve a este menú.
            service.cancel()
            print("Operación interrumpida:", error_message(error))


def observer(db):
    """Cliente de consulta para la defensa. Es otra conexión (otra sesión), así
    que solo ve los datos que la aplicación ya ha confirmado con COMMIT."""
    print("Cliente de consulta: sesión independiente. Solo muestra datos confirmados.")
    while True:
        try:
            show_tables(db)
        except Exception as error:
            print(error_message(error))
        if input("Intro = actualizar; q = salir: ").strip().lower() == "q":
            return


def main():
    parser = argparse.ArgumentParser(description="Seminario 1 DDSI — Python + ODBC + Oracle")
    parser.add_argument("--consulta", action="store_true", help="Cliente de consulta en otra sesión")
    parser.add_argument("--comprobar", action="store_true", help="Comprobar la conexión sin modificar nada")
    parser.add_argument("--probar-oracle", action="store_true", help="Validar las transacciones en Oracle")
    args = parser.parse_args()
    db = None
    status = 0  # Código de salida del programa: 0 = bien, 1 = error.
    try:
        if args.probar_oracle:
            from tests.oracle_integration import run
            run()
            return 0
        db = connect()
        print("Conexión Oracle mediante ODBC establecida. Autocommit desactivado.")
        if args.comprobar:
            # Consulta mínima que no toca ninguna tabla nuestra.
            print_table(*query(db, "SELECT USER AS USUARIO FROM DUAL"))
        elif args.consulta:
            observer(db)
        else:
            main_menu(db)
    except (EOFError, KeyboardInterrupt):
        # Ctrl+C o Ctrl+D en cualquier momento.
        print("\nSalida solicitada. Se deshace cualquier pedido sin confirmar.")
    except Exception as error:
        print("Error:", error_message(error), file=sys.stderr)
        status = 1
    finally:
        # Opción "Salir" y cualquier otra salida: ROLLBACK explícito de lo que
        # quedara pendiente (cerrar nunca debe confirmar un pedido a medias) y
        # cierre de la conexión, para no dejar sesiones colgadas en el servidor.
        if db is not None:
            try:
                db.rollback()
            except Exception:
                print("No se pudo hacer el ROLLBACK final: conexión perdida.", file=sys.stderr)
                status = 1
            finally:
                db.close()
    return status


if __name__ == "__main__":
    sys.exit(main())
