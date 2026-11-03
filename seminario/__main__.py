"""Interfaz de consola requerida por el enunciado."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys
from .db import ROOT, connect, print_table, query, show_tables
from .orders import Orders, positive_integer


def integer(prompt):
    while True:
        try:
            return positive_integer(int(input(prompt)))
        except ValueError as error:
            print(error)


def order_date():
    while True:
        try:
            value = input("Fecha (AAAA-MM-DD, Intro = hoy): ").strip()
            return date.fromisoformat(value) if value else date.today()
        except ValueError:
            print("Introduce una fecha válida en formato AAAA-MM-DD.")


def error_message(error):
    message = str(error)
    if "ORA-00942" in message:
        return "Faltan tablas. Usa la opción 1 del menú principal para crearlas."
    if "ORA-00001" in message:
        return "Ya existe ese código de pedido. Utiliza otro."
    if "ORA-01017" in message:
        return "Usuario o contraseña Oracle incorrectos. La cuenta Oracle puede ser distinta de la cuenta UGR."
    if any(code in message for code in ("ORA-12170", "ORA-12541", "ORA-12154", "HYT00")):
        return "No se puede conectar. Revisa VPN/Eduroam, servidor, puerto y servicio."
    return message


def new_order(service, db):
    service.begin(integer("Código de pedido: "), integer("Código de cliente: "), order_date())
    while True:
        print("\n1. Añadir detalle de producto\n2. Eliminar todos los detalles de producto"
              "\n3. Cancelar pedido\n4. Finalizar pedido")
        option = input("Opción: ").strip()
        if option == "1":
            try:
                service.add(integer("Código de producto: "), integer("Cantidad: "))
                print("Detalle añadido. Cambios pendientes de confirmar.")
            except ValueError as error:
                print(error)
            except Exception as error:
                # add() ha deshecho solo el detalle que falló; mantiene lo anterior.
                print("No se añadió el detalle:", error_message(error))
            show_tables(db)
        elif option == "2":
            service.clear()
            print("Detalles eliminados y stock repuesto; se conserva la cabecera.")
            show_tables(db)
        elif option == "3":
            service.cancel()
            print("Pedido cancelado (ROLLBACK).")
            show_tables(db)
            return
        elif option == "4":
            service.finish()
            print("Pedido confirmado (COMMIT).")
            return
        else:
            print("Opción no válida.")


def main_menu(db):
    service = Orders(db)
    while True:
        print("\n1. Borrar y crear tablas e insertar stock inicial\n2. Dar de alta nuevo pedido"
              "\n3. Mostrar contenido de las tablas\n4. Salir")
        option = input("Opción: ").strip()
        try:
            if option == "1":
                if input("Se borrarán STOCK, PEDIDO y DETALLE_PEDIDO. Escribe BORRAR: ") == "BORRAR":
                    service.reset()
                    print("Tablas creadas e insertadas las 10 tuplas de Stock.")
                    show_tables(db)
            elif option == "2":
                new_order(service, db)
            elif option == "3":
                show_tables(db)
            elif option == "4":
                return
            else:
                print("Opción no válida.")
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as error:
            # Si COMMIT, ROLLBACK o la conexión fallan, no continuar una sesión incierta.
            service.cancel()
            print("Operación interrumpida:", error_message(error))
            import pyodbc
            if isinstance(error, pyodbc.Error) and any(str(a).startswith(("08", "HYT")) for a in error.args):
                raise


def observer(db):
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
    parser.add_argument("--comprobar", action="store_true", help="Comprobar login sin modificar tablas")
    parser.add_argument("--probar-oracle", action="store_true", help="Validar transacciones en tablas de prueba independientes")
    args = parser.parse_args()
    db = None
    status = 0
    try:
        if args.probar_oracle:
            from tests.oracle_integration import run
            run()
            return 0
        db = connect()
        print("Conexión Oracle mediante ODBC establecida. Autocommit desactivado.")
        if args.comprobar:
            headers, rows = query(db, "SELECT USER AS USUARIO, SYS_CONTEXT('USERENV', 'DB_NAME') AS BD FROM DUAL")
            print_table(headers, rows)
            (ROOT / ".local").mkdir(exist_ok=True)
            (ROOT / ".local" / "conexion.json").write_text(json.dumps({"ok": True, "odbc": True}))
        elif args.consulta:
            observer(db)
        else:
            main_menu(db)
    except (EOFError, KeyboardInterrupt):
        print("\nSalida solicitada. Se deshace cualquier pedido sin confirmar.")
    except Exception as error:
        print("Error:", error_message(error), file=sys.stderr)
        status = 1
    finally:
        if db is not None:
            try:
                db.rollback()  # Explícito: cerrar nunca debe confirmar un pedido pendiente.
            except Exception:
                print("No se pudo confirmar el ROLLBACK; conexión perdida.", file=sys.stderr)
                status = 1
            finally:
                db.close()
    return status


if __name__ == "__main__":
    sys.exit(main())
