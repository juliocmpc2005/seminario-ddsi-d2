"""Lógica del seminario: creación de tablas y alta de pedidos con transacciones.

Aquí está TODO el control de transacciones. Resumen de la vida de un pedido:

    begin()   INSERT en PEDIDO  -> Oracle abre la transacción con este primer DML
              SAVEPOINT pedido_sin_detalles
    add()     SAVEPOINT antes_detalle; descuenta STOCK e inserta en DETALLE_PEDIDO
              (si algo falla: ROLLBACK TO antes_detalle, solo se pierde esa línea)
    clear()   ROLLBACK TO pedido_sin_detalles -> sin detalles, con cabecera
    cancel()  ROLLBACK  -> no queda nada del pedido; fin de la transacción
    finish()  COMMIT    -> todo queda permanente; fin de la transacción

Mientras no llega el COMMIT, los cambios solo los ve nuestra sesión.
"""
from .db import ROOT

# Las 10 tuplas predefinidas de STOCK que pide el enunciado: (CPRODUCTO, CANTIDAD).
STOCK_INITIAL = ((1, 100), (2, 80), (3, 60), (4, 40), (5, 20),
                 (6, 150), (7, 75), (8, 50), (9, 30), (10, 10))


class Orders:
    """Operaciones sobre UNA conexión. Una transacción pertenece a su sesión,
    así que todo el pedido debe hacerse por la misma conexión."""

    def __init__(self, connection):
        self.connection = connection
        self.current = None  # Código del pedido que se está dando de alta (o None).

    def execute(self, sql, params=()):
        """Ejecuta una sentencia y devuelve cuántas filas ha modificado.

        Los '?' del SQL son parámetros: el driver envía los valores aparte del
        texto de la sentencia, así que nunca se concatenan datos del usuario.
        """
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        affected = cursor.rowcount
        cursor.close()
        return affected

    # ------------------------------------------------------------------
    # Opción 1 del menú principal
    # ------------------------------------------------------------------
    def reset(self):
        """Borra y vuelve a crear las tres tablas e inserta el stock inicial.

        OJO: en Oracle cada sentencia DDL (DROP, CREATE) hace un COMMIT implícito,
        así que esta operación no se puede deshacer. Por eso solo se ofrece en el
        menú principal y nunca en mitad de un pedido.
        """
        self.connection.rollback()  # Nada pendiente antes de empezar con el DDL.

        # Primero la tabla que tiene claves externas hacia las otras dos.
        for table in ("DETALLE_PEDIDO", "PEDIDO", "STOCK"):
            try:
                self.execute(f"DROP TABLE {table}")
            except Exception as error:
                # ORA-00942 = "la tabla no existe": normal la primera vez.
                if "ORA-00942" not in str(error):
                    raise

        # sql/schema.sql contiene los tres CREATE TABLE separados por ';'.
        # Se quitan las líneas de comentario (las que empiezan por --) y se
        # envía por ODBC una sentencia cada vez, sin el ';' final.
        lines = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8").splitlines()
        schema = "\n".join(line for line in lines if not line.startswith("--"))
        for statement in schema.split(";"):
            if statement.strip():
                self.execute(statement)

        # Los INSERT sí son DML: forman una transacción que confirmamos nosotros.
        for product, quantity in STOCK_INITIAL:
            self.execute("INSERT INTO STOCK VALUES (?, ?)", (product, quantity))
        self.connection.commit()

    # ------------------------------------------------------------------
    # Opción 2 del menú principal: alta de un pedido
    # ------------------------------------------------------------------
    def begin(self, order, client, day):
        """Inserta la cabecera del pedido. Aquí empieza la transacción."""
        self.execute("INSERT INTO PEDIDO VALUES (?, ?, ?)", (order, client, day))
        # Punto de retorno: "pedido creado pero todavía sin ningún detalle".
        # La opción "Eliminar todos los detalles" volverá exactamente aquí.
        self.execute("SAVEPOINT pedido_sin_detalles")
        self.current = order

    def add(self, product, quantity):
        """Añade una línea al pedido si hay stock, y descuenta ese stock."""
        # Savepoint de la línea: descontar stock e insertar el detalle deben
        # ocurrir los dos o ninguno, sin perder las líneas añadidas antes.
        self.execute("SAVEPOINT antes_detalle")
        try:
            # Un único UPDATE comprueba el stock y lo descuenta a la vez: solo
            # modifica la fila si el producto existe y tiene cantidad suficiente.
            affected = self.execute(
                "UPDATE STOCK SET CANTIDAD = CANTIDAD - ? "
                "WHERE CPRODUCTO = ? AND CANTIDAD >= ?", (quantity, product, quantity))
            if affected != 1:
                raise ValueError("Producto inexistente o stock insuficiente.")

            # Si el producto ya estaba en el pedido se suma la cantidad a su
            # línea (la clave primaria impide dos líneas del mismo producto)...
            affected = self.execute(
                "UPDATE DETALLE_PEDIDO SET CANTIDAD = CANTIDAD + ? "
                "WHERE CPEDIDO = ? AND CPRODUCTO = ?", (quantity, self.current, product))
            # ...y si no estaba, se inserta la línea nueva.
            if affected == 0:
                self.execute("INSERT INTO DETALLE_PEDIDO VALUES (?, ?, ?)",
                             (self.current, product, quantity))
        except Exception:
            # Deshace solo lo hecho desde el savepoint de esta línea (por ejemplo,
            # un stock ya descontado). La transacción sigue activa con lo anterior.
            self.execute("ROLLBACK TO antes_detalle")
            raise

    def clear(self):
        """Elimina todos los detalles del pedido pero conserva la cabecera."""
        # Volver al savepoint deshace todos los INSERT de detalles Y todos los
        # descuentos de stock posteriores a él. Un simple DELETE de los detalles
        # no devolvería el stock. La transacción sigue activa y el savepoint
        # sigue existiendo, así que se puede repetir las veces que haga falta.
        self.execute("ROLLBACK TO pedido_sin_detalles")

    def cancel(self):
        """Cancela el pedido: ROLLBACK de toda la transacción."""
        # Desaparecen la cabecera y los detalles, y el stock vuelve a su valor.
        self.connection.rollback()
        self.current = None

    def finish(self):
        """Finaliza el pedido: COMMIT. Los cambios pasan a ser permanentes y
        visibles para las demás sesiones; ya no se pueden deshacer."""
        self.connection.commit()
        self.current = None
